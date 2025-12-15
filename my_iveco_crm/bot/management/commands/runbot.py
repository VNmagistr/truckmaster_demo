import os
import logging
import asyncio
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from orders.models import ServiceOrder
from clients.models import Client, Truck
from bot.models import BotMessageLog
from asgiref.sync import sync_to_async

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
logger = logging.getLogger(__name__)

# --- 1. Клавіатури ---
MAIN_KEYBOARD = [
    [KeyboardButton("Мої автомобілі 🚚")],
    [KeyboardButton("Перевірити статус замовлення 🧾")],
]
MAIN_REPLY_MARKUP = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)

ADMIN_KEYBOARD = [
    [KeyboardButton("Мої автомобілі 🚚"), KeyboardButton("Всі автомобілі 🚛")],
    [KeyboardButton("Перевірити статус замовлення 🧾"), KeyboardButton("Всі замовлення 📋")],
    [KeyboardButton("Знайти авто за номером 🔍")], [KeyboardButton("Статистика 📊")],
]
ADMIN_REPLY_MARKUP = ReplyKeyboardMarkup(ADMIN_KEYBOARD, resize_keyboard=True)

# --- 2. Допоміжні функції ---
@sync_to_async
def check_if_user_is_linked(chat_id):
    try:
        client = Client.objects.get(telegram_chat_id=chat_id)
        return True, client.is_admin
    except Client.DoesNotExist:
        return False, False

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
    except Exception as e:
        logger.error(f"Не вдалося зберегти лог: {e}")

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
        return {"reply_text": "Я не можу знайти ваш профіль. Використайте /start та надайте номер телефону.", "keyboard": None}
    except Exception as e:
        logger.error(f"Помилка get_my_cars: {e}")
        return {"reply_text": "Виникла помилка при пошуку ваших автомобілів.", "keyboard": None}

@sync_to_async
def get_all_trucks():
    """Адмін функція: всі автомобілі"""
    try:
        trucks = Truck.objects.select_related('client').all()[:10]
        
        if not trucks.exists():
            return "В системі немає автомобілів."

        reply = "📋 Всі автомобілі в системі (перші 10):\n\n"
        
        for truck in trucks:
            owner = truck.client.name if truck.client else "Без власника"
            reply += f"🚚 {truck.license_plate} ({truck.specific_model_name})\n"
            reply += f"   Власник: {owner}\n"
            reply += f"   VIN: ...{truck.last_seven_vin}\n\n"
            
        return reply
        
    except Exception as e:
        logger.error(f"Помилка get_all_trucks: {e}")
        return "Не вдалося отримати список автомобілів."

@sync_to_async
def get_all_orders():
    """Адмін функція: всі замовлення"""
    try:
        orders = ServiceOrder.objects.select_related('client', 'truck').order_by('-created_at')[:10]
        
        if not orders.exists():
            return "В системі немає замовлень."

        reply = "📋 Останні 10 замовлень:\n\n"
        
        for order in orders:
            reply += f"🧾 №{order.order_number or 'Н/Д'}\n"
            reply += f"   Клієнт: {order.client.name if order.client else 'Н/Д'}\n"
            reply += f"   Авто: {order.truck.license_plate if order.truck else 'Н/Д'}\n"
            reply += f"   Статус: {order.get_status_display()}\n"
            reply += f"   Дата: {order.created_at.strftime('%d.%m.%Y')}\n\n"
            
        return reply
        
    except Exception as e:
        logger.error(f"Помилка get_all_orders: {e}")
        return "Не вдалося отримати список замовлень."

@sync_to_async
def get_statistics():
    """Адмін функція: статистика"""
    try:
        from django.db.models import Count
        
        total_clients = Client.objects.count()
        total_trucks = Truck.objects.count()
        total_orders = ServiceOrder.objects.count()
        
        orders_by_status = ServiceOrder.objects.values('status').annotate(count=Count('id'))
        
        reply = "📊 Статистика системи:\n\n"
        reply += f"👥 Клієнтів: {total_clients}\n"
        reply += f"🚚 Автомобілів: {total_trucks}\n"
        reply += f"🧾 Замовлень: {total_orders}\n\n"
        reply += "За статусами:\n"
        
        for item in orders_by_status:
            status_display = dict(ServiceOrder.StatusChoices.choices).get(item['status'], item['status'])
            reply += f"  • {status_display}: {item['count']}\n"
            
        return reply
        
    except Exception as e:
        logger.error(f"Помилка get_statistics: {e}")
        return "Не вдалося отримати статистику."

@sync_to_async
def find_truck_by_plate(plate_number):
    """Пошук авто за номером"""
    try:
        plate_clean = plate_number.strip().upper().replace(' ', '')
        trucks = Truck.objects.filter(license_plate__icontains=plate_clean).select_related('client')
        
        if not trucks.exists():
            return f"Автомобіль з номером '{plate_number}' не знайдено."
        
        if trucks.count() == 1:
            truck = trucks.first()
            owner = truck.client.name if truck.client else "Без власника"
            
            reply = f"🚚 Автомобіль знайдено:\n\n"
            reply += f"Номер: {truck.license_plate}\n"
            reply += f"Модель: {truck.specific_model_name}\n"
            reply += f"VIN: ...{truck.last_seven_vin}\n"
            reply += f"Власник: {owner}\n"
            
            # Додаємо історію замовлень
            orders = ServiceOrder.objects.filter(truck=truck).order_by('-created_at')[:5]
            if orders.exists():
                reply += f"\n📋 Останні замовлення:\n"
                for order in orders:
                    reply += f"  • №{order.order_number} - {order.get_status_display()} ({order.created_at.strftime('%d.%m.%Y')})\n"
            
            return reply
        else:
            reply = f"Знайдено {trucks.count()} автомобілів:\n\n"
            for truck in trucks[:10]:
                owner = truck.client.name if truck.client else "Без власника"
                reply += f"🚚 {truck.license_plate} ({truck.specific_model_name})\n"
                reply += f"   Власник: {owner}\n\n"
            return reply
            
    except Exception as e:
        logger.error(f"Помилка find_truck_by_plate: {e}")
        return "Не вдалося знайти автомобіль."

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

        return reply
        
    except Truck.DoesNotExist:
        return "Автомобіль не знайдено."
    except Exception as e:
        logger.error(f"Помилка get_repair_history: {e}")
        return "Виникла помилка при отриманні історії."

@sync_to_async
def get_order_from_db(order_number):
    try:
        order = ServiceOrder.objects.filter(order_number=order_number).select_related('client', 'truck').first()
        
        if not order:
            return f"Замовлення №{order_number} не знайдено."

        truck_info = f"{order.truck.license_plate}" if order.truck else "Не вказано"
        client_info = f"{order.client.name}" if order.client else "Не вказано"
        
        reply = f"🧾 Замовлення-наряд №{order.order_number}\n\n"
        reply += f"Клієнт: {client_info}\n"
        reply += f"Автомобіль: {truck_info}\n"
        reply += f"Статус: {order.get_status_display()}\n"
        reply += f"Дата створення: {order.created_at.strftime('%d.%m.%Y')}\n"
        
        return reply
        
    except Exception as e:
        logger.error(f"Помилка get_order_from_db: {e}")
        return "Виникла помилка при пошуку замовлення."

# --- 3. Обробники ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    message_text = update.message.text
    
    is_linked, is_admin = await check_if_user_is_linked(chat_id)

    if is_linked:
        reply_text = f'Вітаю знову, {user_name}! Оберіть опцію з меню:'
        markup = ADMIN_REPLY_MARKUP if is_admin else MAIN_REPLY_MARKUP
        await update.message.reply_text(reply_text, reply_markup=markup)
    else:
        contact_keyboard = KeyboardButton(text="Надати номер телефону", request_contact=True)
        custom_keyboard = [[contact_keyboard]]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True, one_time_keyboard=True)
        reply_text = (
            f'Вітаю, {user_name}!\n\n'
            'Я не впізнав вас. Для прив\'язки до вашої картки клієнта, поділіться номером телефону.'
        )
        await update.message.reply_text(reply_text, reply_markup=reply_markup)
    
    await log_message(chat_id, user_name, message_text, reply_text)

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    phone_number = update.message.contact.phone_number
    
    reply_text = await link_client_by_phone(chat_id, user_name, phone_number)
    
    is_linked, is_admin = await check_if_user_is_linked(chat_id)
    markup = ADMIN_REPLY_MARKUP if is_admin else MAIN_REPLY_MARKUP
    
    await update.message.reply_text(reply_text, reply_markup=markup) 
    await log_message(chat_id, user_name, f"[Контакт: {phone_number}]", reply_text, phone_number=phone_number)

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

async def all_trucks_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Адмін функція: всі автомобілі"""
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    message_text = update.message.text
    
    # Перевірка адмін прав
    is_linked, is_admin = await check_if_user_is_linked(chat_id)
    if not is_admin:
        reply_text = "У вас немає доступу до цієї функції."
        await update.message.reply_text(reply_text)
        await log_message(chat_id, user_name, message_text, reply_text)
        return
    
    reply_text = await get_all_trucks()
    await update.message.reply_text(reply_text)
    await log_message(chat_id, user_name, message_text, reply_text)

async def all_orders_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Адмін функція: всі замовлення"""
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    message_text = update.message.text
    
    is_linked, is_admin = await check_if_user_is_linked(chat_id)
    if not is_admin:
        reply_text = "У вас немає доступу до цієї функції."
        await update.message.reply_text(reply_text)
        await log_message(chat_id, user_name, message_text, reply_text)
        return
    
    reply_text = await get_all_orders()
    await update.message.reply_text(reply_text)
    await log_message(chat_id, user_name, message_text, reply_text)

async def statistics_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Адмін функція: статистика"""
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    message_text = update.message.text
    
    is_linked, is_admin = await check_if_user_is_linked(chat_id)
    if not is_admin:
        reply_text = "У вас немає доступу до цієї функції."
        await update.message.reply_text(reply_text)
        await log_message(chat_id, user_name, message_text, reply_text)
        return
    
    reply_text = await get_statistics()
    await update.message.reply_text(reply_text)
    await log_message(chat_id, user_name, message_text, reply_text)

async def search_truck_by_plate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Адмін функція: пошук авто за номером"""
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    message_text = update.message.text
    
    is_linked, is_admin = await check_if_user_is_linked(chat_id)
    if not is_admin:
        reply_text = "У вас немає доступу до цієї функції."
        await update.message.reply_text(reply_text)
        await log_message(chat_id, user_name, message_text, reply_text)
        return
    
    reply_text = "Введіть номерний знак автомобіля (наприклад: АА1234ВВ):"
    await update.message.reply_text(reply_text)
    await log_message(chat_id, user_name, message_text, reply_text)
    
    # Встановлюємо стан "очікування номера авто"
    context.user_data['awaiting_truck_plate'] = True

async def ask_for_order_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    message_text = update.message.text
    
    reply_text = "Надішліть номер замовлення-наряду."
    
    await update.message.reply_text(reply_text)
    await log_message(chat_id, user_name, message_text, reply_text)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    original_text = update.message.text
    
    # Перевірка чи очікуємо номер авто
    if context.user_data.get('awaiting_truck_plate'):
        context.user_data['awaiting_truck_plate'] = False
        reply_message = await find_truck_by_plate(original_text)
        await update.message.reply_text(reply_message)
        await log_message(chat_id, user_name, original_text, reply_message)
        return
    
    # Стара логіка для пошуку замовлень
    order_number = re.sub(r'\D', '', original_text)
    
    if not order_number:
        reply_message = "Оберіть опцію з меню або надішліть номер замовлення."
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
        else:
            await query.edit_message_text(text="Невідома дія.")

    except Exception as e:
        logger.error(f"Помилка callback: {e}")
        await query.edit_message_text(text="Сталася помилка.")

# --- 4. Команда Django ---
class Command(BaseCommand):
    help = 'Запускає Telegram бота'

    def handle(self, *args, **options):
        if not BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN не встановлено!")
            return

        self.stdout.write(self.style.SUCCESS('Бот запускається...'))

        application = Application.builder().token(BOT_TOKEN).build()

        # Команди
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
        
        # Кнопки для всіх
        application.add_handler(MessageHandler(filters.Regex("^Мої автомобілі 🚚$"), my_cars))
        application.add_handler(MessageHandler(filters.Regex("^Перевірити статус замовлення 🧾$"), ask_for_order_number))

        # Адмін кнопки
        application.add_handler(MessageHandler(filters.Regex("^Всі автомобілі 🚛$"), all_trucks_admin))
        application.add_handler(MessageHandler(filters.Regex("^Всі замовлення 📋$"), all_orders_admin))
        application.add_handler(MessageHandler(filters.Regex("^Статистика 📊$"), statistics_admin))
        application.add_handler(MessageHandler(filters.Regex("^Знайти авто за номером 🔍$"), search_truck_by_plate))

        # Inline кнопки
        application.add_handler(CallbackQueryHandler(handle_car_selection, pattern='^history_'))
        
        # Текст (номер замовлення)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

        try:
            application.run_polling()
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Бот зупинено.'))
        except Exception as e:
            logger.error(f"Бот впав: {e}")
            raise e