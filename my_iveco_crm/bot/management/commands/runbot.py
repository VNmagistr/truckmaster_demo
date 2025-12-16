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
from bot.models import BotUser, BotMessageLog
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
    [KeyboardButton("Знайти авто за номером 🔍"), KeyboardButton("Знайти клієнта 👤")],
    [KeyboardButton("Статистика 📊")],
]
ADMIN_REPLY_MARKUP = ReplyKeyboardMarkup(ADMIN_KEYBOARD, resize_keyboard=True)

# --- 2. Допоміжні функції ---
@sync_to_async
def get_or_create_bot_user(telegram_user):
    """Отримати або створити BotUser з telegram User об'єкта"""
    try:
        bot_user, created = BotUser.objects.get_or_create(
            telegram_id=telegram_user.id,
            defaults={
                'username': telegram_user.username or '',
                'first_name': telegram_user.first_name or '',
                'last_name': telegram_user.last_name or '',
                'language_code': telegram_user.language_code or 'uk',
                'role': 'guest',
                'is_active': True,
            }
        )
        
        # Оновлюємо інфо при кожному контакті
        if not created:
            updated = False
            if bot_user.username != (telegram_user.username or ''):
                bot_user.username = telegram_user.username or ''
                updated = True
            if bot_user.first_name != (telegram_user.first_name or ''):
                bot_user.first_name = telegram_user.first_name or ''
                updated = True
            if bot_user.last_name != (telegram_user.last_name or ''):
                bot_user.last_name = telegram_user.last_name or ''
                updated = True
            
            if updated:
                bot_user.save()
        
        return bot_user
    except Exception as e:
        logger.error(f"Помилка get_or_create_bot_user: {e}")
        return None

@sync_to_async
def check_if_user_is_linked(telegram_id):
    """Перевірка чи користувач прив'язаний до клієнта"""
    try:
        bot_user = BotUser.objects.select_related('client').get(telegram_id=telegram_id)
        is_linked = bot_user.client is not None
        is_admin = bot_user.role == 'admin'
        return is_linked, is_admin, bot_user
    except BotUser.DoesNotExist:
        return False, False, None

@sync_to_async
def link_bot_user_by_phone(bot_user, phone_number):
    """Прив'язка BotUser до Client через номер телефону"""
    try:
        clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        
        # Шукаємо клієнта за номером
        client = Client.objects.get(phone__contains=clean_phone[-9:])  # Останні 9 цифр
        
        # Прив'язуємо
        bot_user.client = client
        bot_user.phone_number = phone_number
        
        # Якщо клієнт was адмін в старій системі
        if client.is_admin:
            bot_user.role = 'admin'
        elif client.trucks.exists():
            bot_user.role = 'owner'
        else:
            bot_user.role = 'guest'
        
        # Призначаємо автомобілі
        bot_user.assigned_trucks.set(client.trucks.all())
        
        bot_user.save()
        
        # Оновлюємо Client для зворотної сумісності
        client.telegram_chat_id = bot_user.telegram_id
        client.save()
        
        return (
            f"Дякую, {bot_user.first_name}! Я знайшов вас у базі.\n"
            f"Ваш профіль клієнта '{client.name}' успішно прив'язано до цього чату.\n"
            f"Ваша роль: {bot_user.get_role_display()}"
        )
    except Client.DoesNotExist:
        return (
            f"Дякую, {bot_user.first_name}! На жаль, я не знайшов клієнта з номером {phone_number} у нашій базі. "
            "Зверніться до менеджера для реєстрації."
        )
    except Client.MultipleObjectsReturned:
        return (
            f"Виникла помилка: з номером {phone_number} знайдено декілька клієнтів. "
            "Будь ласка, зверніться до менеджера для вирішення."
        )
    except Exception as e:
        logger.error(f"Помилка прив'язки: {e}")
        return "Виникла невідома помилка. Будь ласка, спробуйте пізніше."

@sync_to_async
def log_message_to_db(bot_user, message_text, bot_response, message_type='text', is_incoming=True):
    """Логування повідомлення в БД"""
    try:
        BotMessageLog.objects.create(
            bot_user=bot_user,
            message_type=message_type,
            is_incoming=is_incoming,
            message_text=message_text,
            bot_response=bot_response,
            is_processed=True,
        )
    except Exception as e:
        logger.error(f"Не вдалося зберегти лог: {e}")

@sync_to_async
def get_my_cars_with_keyboard(bot_user):
    """Отримати автомобілі користувача"""
    try:
        if not bot_user.client:
            return {"reply_text": "Ваш профіль не прив'язано до клієнта. Використайте /start", "keyboard": None}
        
        trucks = bot_user.assigned_trucks.all()
        
        if not trucks.exists():
            return {"reply_text": f"За вами ({bot_user.client.name}) не закріплено жодного автомобіля.", "keyboard": None}

        reply_text = "Ваші автомобілі в нашій системі. Оберіть, по якому з них показати історію:"
        
        keyboard = []
        for truck in trucks:
            button = InlineKeyboardButton(
                text=f"🚚 {truck.license_plate} ({truck.specific_model_name})",
                callback_data=f"history_{truck.id}"
            )
            keyboard.append([button])
        
        return {"reply_text": reply_text, "keyboard": InlineKeyboardMarkup(keyboard)}

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
        total_bot_users = BotUser.objects.count()
        linked_users = BotUser.objects.exclude(client__isnull=True).count()
        
        orders_by_status = ServiceOrder.objects.values('status').annotate(count=Count('id'))
        
        reply = "📊 Статистика системи:\n\n"
        reply += f"👥 Клієнтів: {total_clients}\n"
        reply += f"🚚 Автомобілів: {total_trucks}\n"
        reply += f"🧾 Замовлень: {total_orders}\n"
        reply += f"🤖 Користувачів бота: {total_bot_users}\n"
        reply += f"🔗 Прив'язаних: {linked_users}\n\n"
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
def find_client_by_name(search_name):
    """Пошук клієнта за ім'ям"""
    try:
        search_clean = search_name.strip().lower()
        clients = Client.objects.filter(name__icontains=search_clean).prefetch_related('trucks')
        
        if not clients.exists():
            return f"Клієнта з ім'ям '{search_name}' не знайдено."
        
        if clients.count() == 1:
            client = clients.first()
            
            reply = f"👤 Клієнт знайдений:\n\n"
            reply += f"Ім'я: {client.name}\n"
            reply += f"Телефон: {client.phone or 'Не вказано'}\n"
            reply += f"Email: {client.email or 'Не вказано'}\n"
            
            # Автомобілі клієнта
            trucks = client.trucks.all()
            if trucks.exists():
                reply += f"\n🚚 Автомобілі ({trucks.count()}):\n"
                for truck in trucks:
                    reply += f"  • {truck.license_plate} - {truck.specific_model_name}\n"
                    reply += f"    VIN: ...{truck.last_seven_vin}\n"
            else:
                reply += f"\nАвтомобілів не зареєстровано."
            
            return reply
        else:
            reply = f"Знайдено {clients.count()} клієнтів:\n\n"
            for client in clients[:10]:
                trucks_count = client.trucks.count()
                reply += f"👤 {client.name}\n"
                reply += f"   Телефон: {client.phone or 'Н/Д'}\n"
                reply += f"   Автомобілів: {trucks_count}\n\n"
            
            if clients.count() > 10:
                reply += f"...та ще {clients.count() - 10} клієнтів"
            
            return reply
            
    except Exception as e:
        logger.error(f"Помилка find_client_by_name: {e}")
        return "Не вдалося знайти клієнта."

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
    telegram_user = update.message.from_user
    message_text = update.message.text
    
    # Отримуємо або створюємо BotUser
    bot_user = await get_or_create_bot_user(telegram_user)
    
    if not bot_user:
        await update.message.reply_text("Виникла помилка. Спробуйте пізніше.")
        return
    
    is_linked, is_admin, _ = await check_if_user_is_linked(telegram_user.id)

    if is_linked:
        reply_text = f'Вітаю знову, {bot_user.first_name}! Оберіть опцію з меню:'
        markup = ADMIN_REPLY_MARKUP if is_admin else MAIN_REPLY_MARKUP
        await update.message.reply_text(reply_text, reply_markup=markup)
    else:
        contact_keyboard = KeyboardButton(text="Надати номер телефону", request_contact=True)
        custom_keyboard = [[contact_keyboard]]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True, one_time_keyboard=True)
        reply_text = (
            f'Вітаю, {bot_user.first_name}!\n\n'
            'Я не впізнав вас. Для прив\'язки до вашої картки клієнта, поділіться номером телефону.'
        )
        await update.message.reply_text(reply_text, reply_markup=reply_markup)
    
    await log_message_to_db(bot_user, message_text, reply_text, message_type='command')

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user = update.message.from_user
    phone_number = update.message.contact.phone_number
    
    # Отримуємо BotUser
    bot_user = await get_or_create_bot_user(telegram_user)
    
    if not bot_user:
        await update.message.reply_text("Виникла помилка. Спробуйте пізніше.")
        return
    
    # Прив'язуємо до Client
    reply_text = await link_bot_user_by_phone(bot_user, phone_number)
    
    # Перевіряємо знову після прив'язки
    is_linked, is_admin, bot_user = await check_if_user_is_linked(telegram_user.id)
    markup = ADMIN_REPLY_MARKUP if is_admin else MAIN_REPLY_MARKUP
    
    await update.message.reply_text(reply_text, reply_markup=markup) 
    await log_message_to_db(bot_user, f"[Контакт: {phone_number}]", reply_text, message_type='contact')

async def my_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user = update.message.from_user
    message_text = update.message.text
    
    bot_user = await get_or_create_bot_user(telegram_user)
    
    if not bot_user:
        await update.message.reply_text("Виникла помилка.")
        return

    result = await get_my_cars_with_keyboard(bot_user)
    reply_text = result.get("reply_text")
    keyboard = result.get("keyboard")

    await update.message.reply_text(reply_text, reply_markup=keyboard)
    await log_message_to_db(bot_user, message_text, reply_text)

async def all_trucks_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Адмін функція: всі автомобілі"""
    telegram_user = update.message.from_user
    message_text = update.message.text
    
    bot_user = await get_or_create_bot_user(telegram_user)
    
    # Перевірка адмін прав
    is_linked, is_admin, _ = await check_if_user_is_linked(telegram_user.id)
    if not is_admin:
        reply_text = "У вас немає доступу до цієї функції."
        await update.message.reply_text(reply_text)
        await log_message_to_db(bot_user, message_text, reply_text)
        return
    
    reply_text = await get_all_trucks()
    await update.message.reply_text(reply_text)
    await log_message_to_db(bot_user, message_text, reply_text)

async def all_orders_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Адмін функція: всі замовлення"""
    telegram_user = update.message.from_user
    message_text = update.message.text
    
    bot_user = await get_or_create_bot_user(telegram_user)
    
    is_linked, is_admin, _ = await check_if_user_is_linked(telegram_user.id)
    if not is_admin:
        reply_text = "У вас немає доступу до цієї функції."
        await update.message.reply_text(reply_text)
        await log_message_to_db(bot_user, message_text, reply_text)
        return
    
    reply_text = await get_all_orders()
    await update.message.reply_text(reply_text)
    await log_message_to_db(bot_user, message_text, reply_text)

async def statistics_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Адмін функція: статистика"""
    telegram_user = update.message.from_user
    message_text = update.message.text
    
    bot_user = await get_or_create_bot_user(telegram_user)
    
    is_linked, is_admin, _ = await check_if_user_is_linked(telegram_user.id)
    if not is_admin:
        reply_text = "У вас немає доступу до цієї функції."
        await update.message.reply_text(reply_text)
        await log_message_to_db(bot_user, message_text, reply_text)
        return
    
    reply_text = await get_statistics()
    await update.message.reply_text(reply_text)
    await log_message_to_db(bot_user, message_text, reply_text)

async def search_truck_by_plate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Адмін функція: пошук авто за номером"""
    telegram_user = update.message.from_user
    message_text = update.message.text
    
    bot_user = await get_or_create_bot_user(telegram_user)
    
    is_linked, is_admin, _ = await check_if_user_is_linked(telegram_user.id)
    if not is_admin:
        reply_text = "У вас немає доступу до цієї функції."
        await update.message.reply_text(reply_text)
        await log_message_to_db(bot_user, message_text, reply_text)
        return
    
    reply_text = "Введіть номерний знак автомобіля (наприклад: АА1234ВВ):"
    await update.message.reply_text(reply_text)
    await log_message_to_db(bot_user, message_text, reply_text)
    
    # Встановлюємо стан "очікування номера авто"
    context.user_data['awaiting_truck_plate'] = True

async def search_client_by_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Адмін функція: пошук клієнта за ім'ям"""
    telegram_user = update.message.from_user
    message_text = update.message.text
    
    bot_user = await get_or_create_bot_user(telegram_user)
    
    is_linked, is_admin, _ = await check_if_user_is_linked(telegram_user.id)
    if not is_admin:
        reply_text = "У вас немає доступу до цієї функції."
        await update.message.reply_text(reply_text)
        await log_message_to_db(bot_user, message_text, reply_text)
        return
    
    reply_text = "Введіть ім'я клієнта для пошуку:"
    await update.message.reply_text(reply_text)
    await log_message_to_db(bot_user, message_text, reply_text)
    
    # Встановлюємо стан "очікування імені клієнта"
    context.user_data['awaiting_client_name'] = True

async def ask_for_order_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user = update.message.from_user
    message_text = update.message.text
    
    bot_user = await get_or_create_bot_user(telegram_user)
    
    reply_text = "Надішліть номер замовлення-наряду."
    
    await update.message.reply_text(reply_text)
    await log_message_to_db(bot_user, message_text, reply_text)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user = update.message.from_user
    original_text = update.message.text
    
    bot_user = await get_or_create_bot_user(telegram_user)
    
    if not bot_user:
        await update.message.reply_text("Виникла помилка.")
        return
    
    # Перевірка чи очікуємо ім'я клієнта
    if context.user_data.get('awaiting_client_name'):
        context.user_data['awaiting_client_name'] = False
        reply_message = await find_client_by_name(original_text)
        await update.message.reply_text(reply_message)
        await log_message_to_db(bot_user, original_text, reply_message)
        return
    
    # Перевірка чи очікуємо номер авто
    if context.user_data.get('awaiting_truck_plate'):
        context.user_data['awaiting_truck_plate'] = False
        reply_message = await find_truck_by_plate(original_text)
        await update.message.reply_text(reply_message)
        await log_message_to_db(bot_user, original_text, reply_message)
        return
    
    # Стара логіка для пошуку замовлень
    order_number = re.sub(r'\D', '', original_text)
    
    if not order_number:
        reply_message = "Оберіть опцію з меню або надішліть номер замовлення."
        await update.message.reply_text(reply_message)
        await log_message_to_db(bot_user, original_text, reply_message)
        return

    reply_message = await get_order_from_db(order_number)
    await update.message.reply_text(reply_message)
    await log_message_to_db(bot_user, original_text, reply_message)

@sync_to_async
def find_client_by_name(search_name):
    """Пошук клієнта за ім'ям"""
    try:
        from django.db.models import Q
        
        search_clean = search_name.strip()
        
        # Розбиваємо на слова для кращого пошуку
        words = search_clean.split()
        
        # Створюємо умови пошуку для кожного слова
        query = Q()
        for word in words:
            if len(word) >= 2:  # Мінімум 2 символи
                query |= Q(name__icontains=word)
        
        # Якщо не знайдено слів, шукаємо повну фразу
        if not query:
            query = Q(name__icontains=search_clean)
        
        clients = Client.objects.filter(query).prefetch_related('trucks').distinct()
        
        if not clients.exists():
            return f"Клієнта з ім'ям '{search_name}' не знайдено."
        
        if clients.count() == 1:
            client = clients.first()
            
            reply = f"👤 Клієнт знайдений:\n\n"
            reply += f"Ім'я: {client.name}\n"
            reply += f"Телефон: {client.phone or 'Не вказано'}\n"
            reply += f"Email: {client.email or 'Не вказано'}\n"
            
            # Автомобілі клієнта
            trucks = client.trucks.all()
            if trucks.exists():
                reply += f"\n🚚 Автомобілі ({trucks.count()}):\n"
                for truck in trucks:
                    reply += f"  • {truck.license_plate} - {truck.specific_model_name}\n"
                    reply += f"    VIN: ...{truck.last_seven_vin}\n"
            else:
                reply += f"\nАвтомобілів не зареєстровано."
            
            return reply
        else:
            reply = f"Знайдено {clients.count()} клієнтів:\n\n"
            for client in clients[:10]:
                trucks_count = client.trucks.count()
                reply += f"👤 {client.name}\n"
                reply += f"   Телефон: {client.phone or 'Н/Д'}\n"
                reply += f"   Автомобілів: {trucks_count}\n\n"
            
            if clients.count() > 10:
                reply += f"...та ще {clients.count() - 10} клієнтів"
            
            return reply
            
    except Exception as e:
        logger.error(f"Помилка find_client_by_name: {e}")
        return "Не вдалося знайти клієнта."
    
async def handle_car_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    telegram_user = query.from_user
    
    bot_user = await get_or_create_bot_user(telegram_user)
    
    try:
        action, truck_id = callback_data.split('_')
        
        if action == 'history':
            reply_text = await get_repair_history(int(truck_id))
            await query.edit_message_text(text=reply_text)
            await log_message_to_db(bot_user, f"[Callback: {callback_data}]", reply_text, message_type='callback')
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
        application.add_handler(MessageHandler(filters.Regex("^Знайти клієнта 👤$"), search_client_by_name))

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