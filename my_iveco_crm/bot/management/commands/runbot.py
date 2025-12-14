import os
import logging
import asyncio
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from orders.models import ServiceOrder
from clients.models import Client, Truck
from bot.models import BotMessageLog
from asgiref.sync import sync_to_async

# Логування
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

# --- Функції роботи з БД ---

@sync_to_async
def check_if_user_is_linked(chat_id):
    return Client.objects.filter(telegram_chat_id=chat_id).exists()


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
    """
    Знаходить клієнта, повертає список вантажівок та клавіатуру для вибору.
    """
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
def get_client_trucks_for_order(chat_id):
    """
    Повертає список вантажівок клієнта для створення замовлення
    """
    try:
        client = Client.objects.get(telegram_chat_id=chat_id)
        trucks = Truck.objects.filter(client=client)
        
        if not trucks.exists():
            return {"success": False, "message": f"За вами ({client.name}) не закріплено жодного автомобіля."}

        keyboard = []
        for truck in trucks:
            button = InlineKeyboardButton(
                text=f"🚚 {truck.license_plate} ({truck.specific_model_name})",
                callback_data=f"order_truck_{truck.id}"
            )
            keyboard.append([button])
        
        # Кнопка скасування
        keyboard.append([InlineKeyboardButton("❌ Скасувати", callback_data="order_cancel")])
        
        return {
            "success": True, 
            "message": "Оберіть автомобіль для створення замовлення:",
            "keyboard": InlineKeyboardMarkup(keyboard)
        }

    except Client.DoesNotExist:
        return {"success": False, "message": "Я не можу знайти ваш профіль. Використайте /start для прив'язки."}
    except Exception as e:
        logger.error(f"Помилка при отриманні авто клієнта: {e}")
        return {"success": False, "message": "Виникла помилка на сервері."}


@sync_to_async
def create_service_order(chat_id, truck_id, description, mileage=None):
    """
    Створює замовлення-наряд в БД
    """
    try:
        client = Client.objects.get(telegram_chat_id=chat_id)
        truck = Truck.objects.get(id=truck_id, client=client)
        
        # Генеруємо номер замовлення
        last_order = ServiceOrder.objects.order_by('-id').first()
        if last_order and last_order.order_number:
            # Витягуємо число з останнього номера
            match = re.search(r'\d+', last_order.order_number)
            if match:
                next_num = int(match.group()) + 1
            else:
                next_num = 1
        else:
            next_num = 1
        
        order_number = f"TG-{next_num:04d}"
        
        # Створюємо замовлення
        order = ServiceOrder.objects.create(
            order_number=order_number,
            client=client,
            truck=truck,
            problem_description=description,
            status='OPEN'
        )
        
        return {
            "success": True,
            "order_number": order_number,
            "truck": f"{truck.license_plate} ({truck.specific_model_name})"
        }
        
    except Truck.DoesNotExist:
        return {"success": False, "message": "Автомобіль не знайдено або не належить вам."}
    except Exception as e:
        logger.error(f"Помилка створення замовлення: {e}")
        return {"success": False, "message": f"Помилка: {str(e)}"}


@sync_to_async
def get_repair_history(truck_id):
    """
    Отримує історію замовлень-нарядів для конкретної вантажівки.
    """
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
    """
    Виконує синхронний запит до бази даних Django по номеру замовлення.
    """
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


# --- Обробники команд ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Вітає користувача. Перевіряє, чи він прив'язаний.
    """
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    message_text = update.message.text
    
    is_linked = await check_if_user_is_linked(chat_id)

    if is_linked:
        reply_text = f'Вітаю знову, {user_name}! Оберіть опцію з меню:'
        await update.message.reply_text(reply_text, reply_markup=MAIN_REPLY_MARKUP)
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
    """
    Обробляє отриманий контакт і показує головне меню.
    """
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    phone_number = update.message.contact.phone_number
    
    reply_text = await link_client_by_phone(chat_id, user_name, phone_number)
    await update.message.reply_text(reply_text, reply_markup=MAIN_REPLY_MARKUP) 
    await log_message(chat_id, user_name, f"[Надано контакт: {phone_number}]", reply_text, phone_number=phone_number)


async def my_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє команду /mycars АБО натискання кнопки "Мої автомобілі 🚚".
    """
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
    """
    Відповідає на натискання кнопки "Перевірити статус замовлення 🧾".
    """
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    message_text = update.message.text
    
    reply_text = "Будь ласка, надішліть мені номер замовлення-наряду (тільки цифри)."
    
    await update.message.reply_text(reply_text)
    await log_message(chat_id, user_name, message_text, reply_text)


# --- Обробники для створення замовлення ---

async def start_create_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Початок процесу створення замовлення - показує список авто
    """
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    message_text = update.message.text
    
    result = await get_client_trucks_for_order(chat_id)
    
    if not result["success"]:
        await update.message.reply_text(result["message"])
        await log_message(chat_id, user_name, message_text, result["message"])
        return ConversationHandler.END
    
    await update.message.reply_text(result["message"], reply_markup=result["keyboard"])
    await log_message(chat_id, user_name, message_text, result["message"])
    
    return SELECTING_TRUCK


async def truck_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє вибір автомобіля
    """
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    user_name = query.from_user.first_name
    
    if query.data == "order_cancel":
        await query.edit_message_text("❌ Створення замовлення скасовано.")
        await log_message(chat_id, user_name, "[Скасування створення замовлення]", "Створення замовлення скасовано.")
        return ConversationHandler.END
    
    # Зберігаємо ID вантажівки в context
    truck_id = query.data.split('_')[-1]
    context.user_data['truck_id'] = truck_id
    
    reply_text = "Опишіть проблему або причину звернення:"
    await query.edit_message_text(reply_text)
    await log_message(chat_id, user_name, f"[Вибрано авто ID: {truck_id}]", reply_text)
    
    return ENTERING_DESCRIPTION


async def description_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє введений опис проблеми
    """
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    description = update.message.text
    
    # Зберігаємо опис
    context.user_data['description'] = description
    
    # Створюємо замовлення
    truck_id = context.user_data.get('truck_id')
    
    result = await create_service_order(chat_id, truck_id, description)
    
    if result["success"]:
        reply_text = (
            f"✅ Замовлення успішно створено!\n\n"
            f"📋 Номер: {result['order_number']}\n"
            f"🚚 Автомобіль: {result['truck']}\n"
            f"📝 Опис: {description}\n\n"
            f"Наш менеджер зв'яжеться з вами найближчим часом."
        )
    else:
        reply_text = f"❌ Помилка при створенні замовлення: {result['message']}"
    
    await update.message.reply_text(reply_text, reply_markup=MAIN_REPLY_MARKUP)
    await log_message(chat_id, user_name, description, reply_text)
    
    # Очищаємо дані
    context.user_data.clear()
    
    return ConversationHandler.END


async def cancel_order_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Скасування створення замовлення
    """
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    
    reply_text = "❌ Створення замовлення скасовано."
    await update.message.reply_text(reply_text, reply_markup=MAIN_REPLY_MARKUP)
    await log_message(chat_id, user_name, "/cancel", reply_text)
    
    context.user_data.clear()
    return ConversationHandler.END


# --- Інші обробники ---

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє будь-яке текстове повідомлення, яке не є командою або кнопкою.
    Припускає, що це номер замовлення.
    """
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    original_text = update.message.text
    
    order_number = re.sub(r'\D', '', original_text)
    
    if not order_number:
        reply_message = "❓ Вибачте, я не зрозумів.\nОберіть опцію з меню або надішліть номер замовлення."
        await update.message.reply_text(reply_message, reply_markup=MAIN_REPLY_MARKUP)
        await log_message(chat_id, user_name, original_text, reply_message)
        return

    reply_message = await get_order_from_db(order_number)
    await update.message.reply_text(reply_message, reply_markup=MAIN_REPLY_MARKUP)
    await log_message(chat_id, user_name, original_text, reply_message)


async def handle_car_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє натискання на кнопки з вибором автомобіля для перегляду історії.
    """
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
        else:
            await query.edit_message_text(text="Невідома дія.")

    except Exception as e:
        logger.error(f"Помилка обробки callback: {e}")
        await query.edit_message_text(text="Сталася помилка при обробці вашого запиту.")


# --- Django Command ---

class Command(BaseCommand):
    help = 'Запускає Telegram бота'

    def handle(self, *args, **options):
        if not BOT_TOKEN:
            logger.error("ПОМИЛКА: Змінна оточення TELEGRAM_BOT_TOKEN не встановлена!")
            return

        self.stdout.write(self.style.SUCCESS('Бот запускається...'))

        application = Application.builder().token(BOT_TOKEN).build()

        # ConversationHandler для створення замовлення
        order_conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^Створити замовлення ➕$"), start_create_order)
            ],
            states={
                SELECTING_TRUCK: [
                    CallbackQueryHandler(truck_selected, pattern='^order_')
                ],
                ENTERING_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, description_entered)
                ],
            },
            fallbacks=[
                CommandHandler('cancel', cancel_order_creation)
            ],
        )

        # Додаємо обробники
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
        
        # ConversationHandler для створення замовлення
        application.add_handler(order_conv_handler)
        
        # Обробники для кнопок головного меню
        application.add_handler(MessageHandler(filters.Regex("^Мої автомобілі 🚚$"), my_cars))
        application.add_handler(MessageHandler(filters.Regex("^Перевірити статус замовлення 🧾$"), ask_for_order_number))

        # Обробник кнопок (Inline) для вибору авто (історія)
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