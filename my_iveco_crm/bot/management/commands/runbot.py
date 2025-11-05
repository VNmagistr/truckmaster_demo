import os
import logging
import asyncio
import re
from django.conf import settings
from django.core.management.base import BaseCommand
# 👇 Нові імпорти для кнопок
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from orders.models import ServiceOrder
from clients.models import Client, Truck
from bot.models import BotMessageLog
from asgiref.sync import sync_to_async

# ... (код логування та BOT_TOKEN) ...
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
logger = logging.getLogger(__name__)

# --- Функції роботи з БД (link_client, log_message, check_if_user_is_linked) ---
# ... (Весь код цих функцій залишається БЕЗ ЗМІН) ...
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

# --- ОНОВЛЕНА ФУНКЦІЯ get_my_cars ---
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
        
        # Створюємо список кнопок
        keyboard = []
        for truck in trucks:
            # `callback_data` - це унікальний ідентифікатор, який прийде нам при натисканні
            # Ми використаємо 'history_TRUCKID' (напр. 'history_12')
            button = InlineKeyboardButton(
                text=f"🚚 {truck.license_plate} ({truck.specific_model_name})",
                callback_data=f"history_{truck.id}"
            )
            keyboard.append([button]) # Кожна кнопка на новому рядку
        
        return {"reply_text": reply_text, "keyboard": InlineKeyboardMarkup(keyboard)}

    except Client.DoesNotExist:
        return {"reply_text": "Я не можу знайти ваш профіль. Будь ласка, спочатку використайте команду /start та надайте свій номер телефону.", "keyboard": None}
    except Exception as e:
        logger.error(f"Помилка під час get_my_cars: {e}")
        return {"reply_text": "Виникла помилка на сервері при пошуку ваших автомобілів.", "keyboard": None}

# --- НОВА ФУНКЦІЯ для історії ремонтів ---
@sync_to_async
def get_repair_history(truck_id):
    """
    Отримує історію замовлень-нарядів для конкретної вантажівки.
    """
    try:
        truck = Truck.objects.get(id=truck_id)
        # Знаходимо всі замовлення для цієї вантажівки, сортуємо від нових до старих
        orders = ServiceOrder.objects.filter(truck=truck).order_by('-created_at')
        
        if not orders.exists():
            return f"Для автомобіля {truck.license_plate} ще немає історії ремонтів."

        reply = f"Історія ремонтів для {truck.license_plate} ({truck.specific_model_name}):\n\n"
        
        # Обмежимо, наприклад, 5-ма останніми
        for order in orders[:5]: 
            reply += f"🧾 Замовлення №{order.order_number} від {order.created_at.strftime('%d.%m.%Y')}\n"
            reply += f"   Статус: {order.get_status_display()}\n"
            # Можна додати опис робіт, якщо він є
            # reply += f"   Опис: {order.problem_description}\n\n"
            reply += "\n"

        if orders.count() > 5:
            reply += f"...та ще {orders.count() - 5} записів."
            
        return reply
        
    except Exception as e:
        logger.error(f"Помилка під час get_repair_history: {e}")
        return "Не вдалося отримати історію ремонтів."

# --- Обробники ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (ця функція залишається без змін)
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    message_text = update.message.text
    is_linked = await check_if_user_is_linked(chat_id)
    if is_linked:
        reply_text = (
            f'Вітаю знову, {user_name}!\n\n'
            'Надішліть мені номер вашого замовлення-наряду, щоб перевірити його статус, або використайте команду /mycars, щоб побачити ваші автомобілі.'
        )
        await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())
    else:
        contact_keyboard = KeyboardButton(text="Надати номер телефону", request_contact=True)
        custom_keyboard = [[contact_keyboard]]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True, one_time_keyboard=True)
        reply_text = (
            f'Вітаю, {user_name}!\n\n'
            'Я не впізнав вас. Для прив\'язки до вашої картки клієнта, будь ласка, поділіться номером телефону, натиснувши кнопку нижче.\n\n'
            'Або просто надішліть мені номер вашого замовлення-наряду.'
        )
        await update.message.reply_text(reply_text, reply_markup=reply_markup)
    await log_message(chat_id, user_name, message_text, reply_text)


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (ця функція залишається без змін)
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    phone_number = update.message.contact.phone_number
    reply_text = await link_client_by_phone(chat_id, user_name, phone_number)
    await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove()) 
    await log_message(chat_id, user_name, f"[Надано контакт: {phone_number}]", reply_text, phone_number=phone_number)


async def check_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (ця функція залишається без змін)
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    original_text = update.message.text
    order_number = re.sub(r'\D', '', original_text)
    if not order_number:
        reply_message = f"'{original_text}' Мені поки що невідома ця команда. Спробуйте, будь ласка, пізніше."
        await update.message.reply_text(reply_message)
        await log_message(chat_id, user_name, original_text, reply_message)
        return
    reply_message = await get_order_from_db(order_number)
    await update.message.reply_text(reply_message)
    await log_message(chat_id, user_name, original_text, reply_message)


# --- ОНОВЛЕНИЙ ОБРОБНИК КОМАНДИ /mycars ---
async def my_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє команду /mycars та викликає функцію get_my_cars_with_keyboard.
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

# --- НОВИЙ ОБРОБНИК НАТИСКАНЬ КНОПОК ---
async def handle_car_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє натискання на кнопки з вибором автомобіля.
    """
    query = update.callback_query
    await query.answer() # Обов'язково відповідаємо на запит кнопки

    # Отримуємо дані, які ми зашили в кнопку (напр. 'history_12')
    callback_data = query.data
    chat_id = query.message.chat.id
    user_name = query.from_user.first_name
    
    try:
        # Витягуємо ID вантажівки з 'history_12'
        action, truck_id = callback_data.split('_')
        
        if action == 'history':
            reply_text = await get_repair_history(int(truck_id))
            # Редагуємо повідомлення, щоб прибрати кнопки
            await query.edit_message_text(text=reply_text)
            await log_message(chat_id, user_name, f"[Callback: {callback_data}]", reply_text)
        else:
            await query.edit_message_text(text="Невідома дія.")

    except Exception as e:
        logger.error(f"Помилка обробки callback: {e}")
        await query.edit_message_text(text="Сталася помилка при обробці вашого запиту.")


@sync_to_async
def get_order_from_db(order_number):
    # ... (ця функція залишається без змін)
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

# --- Клас команди Django ---
class Command(BaseCommand):
    help = 'Запускає Telegram бота'

    def handle(self, *args, **options):
        # ... (код перевірки токена без змін)
        if not BOT_TOKEN:
            logger.error("ПОМИЛКА: Змінна оточення TELEGRAM_BOT_TOKEN не встановлена!")
            return

        self.stdout.write(self.style.SUCCESS('Бот запускається...'))

        application = Application.builder().token(BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("mycars", my_cars))
        application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_order_status))
        # 👇 ДОДАЄМО ОБРОБНИК КНОПОК 👇
        application.add_handler(CallbackQueryHandler(handle_car_selection, pattern='^history_'))


        # ... (код запуску без змін)
        try:
            application.run_polling()
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Бот зупинено.'))
        except Exception as e:
            logger.error(f"Бот впав з помилкою: {e}")
            raise e