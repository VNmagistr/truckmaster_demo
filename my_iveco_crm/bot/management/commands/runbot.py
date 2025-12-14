# bot/management/commands/runbot.py
# ОНОВЛЕНО: Перевірка адміна через UserProfile.role замість змінної оточення

import os
import logging
import re
from django.core.management.base import BaseCommand
from django.conf import settings
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from asgiref.sync import sync_to_async

from orders.models import ServiceOrder
from clients.models import Client, Truck
from bot.models import BotMessageLog
from django.contrib.auth.models import User

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# --- Стани для ConversationHandler ---
SELECTING_TRUCK, ENTERING_DESCRIPTION, ENTERING_MILEAGE = range(3)

# --- Головна клавіатура ---
MAIN_KEYBOARD = [
    [KeyboardButton("Мої автомобілі 🚚")],
    [KeyboardButton("Перевірити статус замовлення 🧾")],
    [KeyboardButton("Створити замовлення ➕")],
]
MAIN_REPLY_MARKUP = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)

# --- Адміністраторська клавіатура ---
ADMIN_KEYBOARD = [
    [KeyboardButton("Мої автомобілі 🚚")],
    [KeyboardButton("Перевірити статус замовлення 🧾")],
    [KeyboardButton("Створити замовлення ➕")],
    [KeyboardButton("📊 Логи бота"), KeyboardButton("🔍 Перевірити автомобіль")],
]
ADMIN_REPLY_MARKUP = ReplyKeyboardMarkup(ADMIN_KEYBOARD, resize_keyboard=True)

# --- Функції роботи з БД ---

@sync_to_async
def check_if_user_is_linked(chat_id):
    return Client.objects.filter(telegram_chat_id=chat_id).exists()


@sync_to_async
def is_admin(chat_id):
    """
    Перевіряє чи користувач є адміністратором через UserProfile.role
    """
    try:
        # Спочатку знаходимо Client по telegram_chat_id
        client = Client.objects.get(telegram_chat_id=chat_id)
        
        # Потім шукаємо User який прив'язаний до цього Client
        # Можна прив'язати через email або phone
        user = User.objects.filter(email=client.email).first()
        
        if not user and client.phone:
            # Якщо не знайшли по email, шукаємо по phone в UserProfile
            from users.models import UserProfile
            profile = UserProfile.objects.filter(phone=client.phone).first()
            if profile:
                user = profile.user
        
        if user and hasattr(user, 'profile'):
            return user.profile.role == 'admin'
        
        return False
    except Client.DoesNotExist:
        return False
    except Exception as e:
        logger.error(f"Помилка перевірки адміна: {e}")
        return False


@sync_to_async
def link_client_by_phone(chat_id, user_name, phone_number):
    try:
        clean_phone = phone_number.replace('+', '')
        client = Client.objects.get(phone__contains=clean_phone)
        client.telegram_chat_id = chat_id
        if not client.name:
            client.name = user_name
        client.save()
        return (
            f"Дякую, {user_name}! Я знайшов вас у базі.\n"
            f"Ваш профіль клієнта '{client.name}' успішно прив'язано до цього чату."
        )
    except Client.DoesNotExist:
        return (
            f"Дякую, {user_name}! На жаль, я не знайшов клієнта з номером {phone_number} у нашій базі. "
            "Зверніться до менеджера для реєстрації."
        )
    except Client.MultipleObjectsReturned:
        return (
            f"Виникла помилка: з номером {phone_number} знайдено декілька клієнтів. "
            "Будь ласка, зверніться до менеджера для вирішення."
        )
    except Exception as e:
        logger.error(f"Помилка прив'язки клієнта: {e}")
        return "Виникла невідома помилка. Будь ласка, спробуйте пізніше."


@sync_to_async
def log_message(chat_id, user_name, message_text, bot_response, phone_number=None):
    try:
        if not phone_number:
            client = Client.objects.filter(telegram_chat_id=chat_id).first()
            if client and client.phone:
                phone_number = client.phone
        
        BotMessageLog.objects.create(
            chat_id=chat_id,
            user_name=user_name,
            phone_number=phone_number,
            message_text=message_text,
            bot_response=bot_response
        )
        logger.info(f"Лог збережено для {chat_id}")
    except Exception as e:
        logger.error(f"Не вдалося зберегти лог для {chat_id}: {e}")


@sync_to_async
def get_my_cars_with_keyboard(chat_id):
    try:
        client = Client.objects.get(telegram_chat_id=chat_id)
        trucks = Truck.objects.filter(client=client)
        
        if not trucks.exists():
            return {"reply_text": f"За вами ({client.name}) не закріплено жодного автомобіля.", "keyboard": None}

        reply_text = "Ваші автомобілі в нашій системі. Оберіть, по якому з них показати історію:"
        
        keyboard = []
        for truck in trucks:
            button = InlineKeyboardButton(
                text=f"🚚 {truck.license_plate} ({truck.specific_model_name})",
                callback_data=f"history_{truck.id}"
            )
            keyboard.append([button])
        
        return {"reply_text": reply_text, "keyboard": InlineKeyboardMarkup(keyboard)}

    except Client.DoesNotExist:
        return {"reply_text": "Я не можу знайти ваш профіль. Будь ласка, спочатку використайте команду /start та надайте свій номер телефону.", "keyboard": None}
    except Exception as e:
        logger.error(f"Помилка під час get_my_cars: {e}")
        return {"reply_text": "Виникла помилка на сервері при пошуку ваших автомобілів.", "keyboard": None}


@sync_to_async
def get_repair_history(truck_id):
    try:
        truck = Truck.objects.get(id=truck_id)
        orders = ServiceOrder.objects.filter(truck=truck).order_by('-created_at')
        
        if not orders.exists():
            return f"Для автомобіля {truck.license_plate} ще немає історії ремонтів."

        reply = f"Історія ремонтів для {truck.license_plate} ({truck.specific_model_name}):\n\n"
        
        for order in orders[:5]: 
            reply += f"🧾 Замовлення №{order.order_number} від {order.created_at.strftime('%d.%m.%Y')}\n"
            reply += f"   Статус: {order.get_status_display()}\n\n"

        if orders.count() > 5:
            reply += f"...та ще {orders.count() - 5} записів."
            
        return reply
        
    except Exception as e:
        logger.error(f"Помилка під час get_repair_history: {e}")
        return "Не вдалося отримати історію ремонтів."


@sync_to_async
def get_order_from_db(order_number):
    try:
        order = ServiceOrder.objects.select_related('client', 'truck').get(order_number=order_number)
        reply = (
            f"Замовлення №{order.order_number}\n"
            f"Статус: {order.get_status_display()}\n"
            f"Клієнт: {order.client.name}\n"
            f"Вантажівка: {order.truck.license_plate}"
        )
        return reply
    except ServiceOrder.DoesNotExist:
        return f"Замовлення з номером {order_number} не знайдено. Будь ласка, перевірте номер."
    except Exception as e:
        logger.error(f"Помилка під час запиту до БД: {e}")
        return "Виникла помилка на сервері. Ми вже працюємо над цим."


@sync_to_async
def get_client_trucks(chat_id):
    try:
        client = Client.objects.get(telegram_chat_id=chat_id)
        trucks = Truck.objects.filter(client=client)
        
        if not trucks.exists():
            return []
        
        return [
            {
                'id': truck.id,
                'license_plate': truck.license_plate,
                'model': truck.specific_model_name
            }
            for truck in trucks
        ]
    except Client.DoesNotExist:
        return []
    except Exception as e:
        logger.error(f"Помилка отримання вантажівок: {e}")
        return []


@sync_to_async
def create_service_order(chat_id, truck_id, description, mileage=None):
    try:
        client = Client.objects.get(telegram_chat_id=chat_id)
        truck = Truck.objects.get(id=truck_id, client=client)
        
        order = ServiceOrder.objects.create(
            client=client,
            truck=truck,
            problem_description=description,
            status='OPEN'
        )
        
        return f"✅ Замовлення успішно створено!\n\nНомер: {order.id}\nАвто: {truck.license_plate}\nОпис: {description}"
        
    except Exception as e:
        logger.error(f"Помилка створення замовлення: {e}")
        return "❌ Помилка при створенні замовлення. Спробуйте пізніше."


# --- АДМІНІСТРАТОРСЬКІ ФУНКЦІЇ ---

@sync_to_async
def get_bot_logs(limit=10):
    """
    Отримує останні записи з логів бота
    """
    try:
        logs = BotMessageLog.objects.all().order_by('-created_at')[:limit]
        
        if not logs:
            return "📊 Логи порожні"
        
        reply = f"📊 Останні {limit} записів:\n\n"
        
        for log in logs:
            reply += f"👤 {log.user_name} ({log.phone_number or 'N/A'})\n"
            reply += f"💬 {log.message_text[:50]}...\n"
            reply += f"🤖 {log.bot_response[:50]}...\n"
            reply += f"🕒 {log.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            reply += "---\n"
        
        return reply
        
    except Exception as e:
        logger.error(f"Помилка отримання логів: {e}")
        return "❌ Помилка отримання логів"


@sync_to_async
def check_truck_by_number(license_plate):
    """
    Знаходить авто по номеру і повертає інформацію
    """
    try:
        truck = Truck.objects.select_related('client', 'base_model').get(license_plate=license_plate)
        
        reply = f"🚚 Автомобіль: {truck.license_plate}\n"
        reply += f"📋 Модель: {truck.specific_model_name}\n"
        reply += f"🔢 VIN (останні 7): {truck.last_seven_vin}\n"
        reply += f"👤 Власник: {truck.client.name if truck.client else 'N/A'}\n"
        reply += f"📞 Телефон: {truck.client.phone if truck.client else 'N/A'}\n\n"
        
        # Історія замовлень
        orders = ServiceOrder.objects.filter(truck=truck).order_by('-created_at')[:5]
        if orders:
            reply += "📝 Останні замовлення:\n"
            for order in orders:
                reply += f"  • №{order.order_number} - {order.get_status_display()} ({order.created_at.strftime('%d.%m.%Y')})\n"
        else:
            reply += "📝 Немає історії замовлень\n"
        
        return reply
        
    except Truck.DoesNotExist:
        return f"❌ Автомобіль з номером {license_plate} не знайдено в базі"
    except Exception as e:
        logger.error(f"Помилка пошуку авто: {e}")
        return "❌ Помилка пошуку автомобіля"


# --- Обробники ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    message_text = update.message.text
    
    is_linked = await check_if_user_is_linked(chat_id)
    user_is_admin = await is_admin(chat_id)
    
    if is_linked or user_is_admin:
        reply_text = f'Вітаю знову, {user_name}! Оберіть опцію з меню:'
        reply_markup = ADMIN_REPLY_MARKUP if user_is_admin else MAIN_REPLY_MARKUP
        await update.message.reply_text(reply_text, reply_markup=reply_markup)
    else:
        contact_keyboard = KeyboardButton(text="Надати номер телефону", request_contact=True)
        custom_keyboard = [[contact_keyboard]]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True, one_time_keyboard=True)
        reply_text = (
            f'Вітаю, {user_name}!\n\n'
            'Я не впізнав вас. Для прив\'язки до вашої картки клієнта, будь ласка, поділіться номером телефону, натиснувши кнопку нижче.'
        )
        await update.message.reply_text(reply_text, reply_markup=reply_markup)
    
    await log_message(chat_id, user_name, message_text, reply_text)


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    phone_number = update.message.contact.phone_number
    
    reply_text = await link_client_by_phone(chat_id, user_name, phone_number)
    
    user_is_admin = await is_admin(chat_id)
    reply_markup = ADMIN_REPLY_MARKUP if user_is_admin else MAIN_REPLY_MARKUP
    
    await update.message.reply_text(reply_text, reply_markup=reply_markup)
    await log_message(chat_id, user_name, f"[Надано контакт: {phone_number}]", reply_text, phone_number=phone_number)


async def my_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    message_text = update.message.text

    result = await get_my_cars_with_keyboard(chat_id)
    reply_text = result.get("reply_text")
    keyboard = result.get("keyboard")

    await update.message.reply_text(reply_text, reply_markup=keyboard)
    await log_message(chat_id, user_name, message_text, reply_text)


async def ask_for_order_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    message_text = update.message.text
    
    reply_text = "Будь ласка, надішліть мені номер замовлення-наряду (тільки цифри)."
    
    await update.message.reply_text(reply_text)
    await log_message(chat_id, user_name, message_text, reply_text)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    original_text = update.message.text
    
    # Перевірка чи чекаємо номер автомобіля (адмін-функція)
    if context.user_data.get('waiting_for_truck_number'):
        context.user_data['waiting_for_truck_number'] = False
        reply_message = await check_truck_by_number(original_text.strip())
        await update.message.reply_text(reply_message, reply_markup=ADMIN_REPLY_MARKUP)
        await log_message(chat_id, user_name, original_text, reply_message)
        return
    
    order_number = re.sub(r'\D', '', original_text)
    
    if not order_number:
        reply_message = "Вибачте, я не зрозумів. Оберіть опцію з меню або надішліть номер замовлення."
        await update.message.reply_text(reply_message)
        await log_message(chat_id, user_name, original_text, reply_message)
        return

    reply_message = await get_order_from_db(order_number)
    await update.message.reply_text(reply_message)
    await log_message(chat_id, user_name, original_text, reply_message)


async def handle_car_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    chat_id = query.message.chat.id
    user_name = query.from_user.first_name
    
    try:
        action, truck_id = callback_data.split('_')
        
        if action == 'history':
            reply_text = await get_repair_history(int(truck_id))
            await query.edit_message_text(text=reply_text)
            await log_message(chat_id, user_name, f"[Callback: {callback_data}]", reply_text)
        elif action == 'select':
            context.user_data['selected_truck_id'] = int(truck_id)
            reply_text = "✍️ Опишіть проблему:"
            await query.edit_message_text(text=reply_text)
            await log_message(chat_id, user_name, f"[Вибрано авто: {truck_id}]", reply_text)
            return ENTERING_DESCRIPTION
        else:
            await query.edit_message_text(text="Невідома дія.")

    except Exception as e:
        logger.error(f"Помилка обробки callback: {e}")
        await query.edit_message_text(text="Сталася помилка при обробці вашого запиту.")


# --- АДМІНІСТРАТОРСЬКІ ОБРОБНИКИ ---

async def show_bot_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показує логи бота (тільки для адміністратора)
    """
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    
    # Перевіряємо чи це адміністратор
    if not await is_admin(chat_id):
        reply_text = "❌ У вас немає доступу до цієї функції."
        await update.message.reply_text(reply_text)
        await log_message(chat_id, user_name, update.message.text, reply_text)
        return
    
    reply_text = await get_bot_logs(limit=10)
    await update.message.reply_text(reply_text, reply_markup=ADMIN_REPLY_MARKUP)
    await log_message(chat_id, user_name, update.message.text, "Показано логи бота")


async def check_truck_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запитує номер автомобіля для перевірки (тільки для адміністратора)
    """
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    
    # Перевіряємо чи це адміністратор
    if not await is_admin(chat_id):
        reply_text = "❌ У вас немає доступу до цієї функції."
        await update.message.reply_text(reply_text)
        await log_message(chat_id, user_name, update.message.text, reply_text)
        return
    
    # Встановлюємо прапорець, що чекаємо на номер авто
    context.user_data['waiting_for_truck_number'] = True
    
    reply_text = "🔍 Введіть номер автомобіля (наприклад: AA1234BB):"
    await update.message.reply_text(reply_text, reply_markup=ADMIN_REPLY_MARKUP)
    await log_message(chat_id, user_name, update.message.text, reply_text)


# --- ConversationHandler для створення замовлення ---

async def start_order_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    
    trucks = await get_client_trucks(chat_id)
    
    if not trucks:
        reply_text = "У вас немає зареєстрованих автомобілів. Зверніться до менеджера."
        await update.message.reply_text(reply_text)
        await log_message(chat_id, user_name, update.message.text, reply_text)
        return ConversationHandler.END
    
    keyboard = []
    for truck in trucks:
        button = InlineKeyboardButton(
            text=f"🚚 {truck['license_plate']} ({truck['model']})",
            callback_data=f"select_{truck['id']}"
        )
        keyboard.append([button])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_text = "Оберіть автомобіль для створення замовлення:"
    
    await update.message.reply_text(reply_text, reply_markup=reply_markup)
    await log_message(chat_id, user_name, update.message.text, reply_text)
    
    return SELECTING_TRUCK


async def description_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    description = update.message.text
    
    truck_id = context.user_data.get('selected_truck_id')
    
    if not truck_id:
        reply_text = "❌ Помилка: авто не вибрано. Почніть спочатку /start"
        await update.message.reply_text(reply_text)
        return ConversationHandler.END
    
    result = await create_service_order(chat_id, truck_id, description)
    
    user_is_admin = await is_admin(chat_id)
    reply_markup = ADMIN_REPLY_MARKUP if user_is_admin else MAIN_REPLY_MARKUP
    
    await update.message.reply_text(result, reply_markup=reply_markup)
    await log_message(chat_id, user_name, description, result)
    
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = user.id
    
    user_is_admin = await is_admin(chat_id)
    reply_markup = ADMIN_REPLY_MARKUP if user_is_admin else MAIN_REPLY_MARKUP
    
    await update.message.reply_text("Створення замовлення скасовано.", reply_markup=reply_markup)
    context.user_data.clear()
    return ConversationHandler.END


# --- Клас команди Django ---
class Command(BaseCommand):
    help = 'Запускає Telegram бота'

    def handle(self, *args, **options):
        if not BOT_TOKEN:
            logger.error("ПОМИЛКА: Змінна оточення TELEGRAM_BOT_TOKEN не встановлена!")
            return

        self.stdout.write(self.style.SUCCESS('Бот запускається...'))

        application = Application.builder().token(BOT_TOKEN).build()

        # ConversationHandler для створення замовлення
        conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^Створити замовлення ➕$"), start_order_creation)
            ],
            states={
                SELECTING_TRUCK: [CallbackQueryHandler(handle_car_selection, pattern='^select_')],
                ENTERING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_entered)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )

        # Обробники команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
        
        # Обробники кнопок головного меню
        application.add_handler(MessageHandler(filters.Regex("^Мої автомобілі 🚚$"), my_cars))
        application.add_handler(MessageHandler(filters.Regex("^Перевірити статус замовлення 🧾$"), ask_for_order_number))

        # АДМІНІСТРАТОРСЬКІ обробники
        application.add_handler(MessageHandler(filters.Regex("^📊 Логи бота$"), show_bot_logs))
        application.add_handler(MessageHandler(filters.Regex("^🔍 Перевірити автомобіль$"), check_truck_prompt))

        # ConversationHandler
        application.add_handler(conv_handler)

        # Обробник кнопок (Inline) для вибору авто
        application.add_handler(CallbackQueryHandler(handle_car_selection, pattern='^history_'))
        
        # Обробник будь-якого іншого тексту
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

        try:
            application.run_polling()
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Бот зупинено.'))
        except Exception as e:
            logger.error(f"Бот впав з помилкою: {e}")
            raise e