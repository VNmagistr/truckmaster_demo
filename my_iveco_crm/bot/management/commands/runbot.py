import os
import logging
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.error import Forbidden, BadRequest, NetworkError
from orders.models import ServiceOrder
from clients.models import Client, Truck
from bot.models import BotMessageLog, BotUser
from asgiref.sync import sync_to_async

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# ============================================================
# КЛАВІАТУРИ ДЛЯ РІЗНИХ РОЛЕЙ
# ============================================================

# Гість - тільки перевірка статусу
GUEST_KEYBOARD = [
    [KeyboardButton("📞 Прив'язати телефон", request_contact=True)],
    [KeyboardButton("Перевірити статус замовлення 🧾")],
]

# Водій - замовлення доступних авто
DRIVER_KEYBOARD = [
    [KeyboardButton("Мої автомобілі 🚚")],
    [KeyboardButton("Перевірити статус замовлення 🧾")],
]

# Власник - все своє
OWNER_KEYBOARD = [
    [KeyboardButton("Мої автомобілі 🚚")],
    [KeyboardButton("Перевірити статус замовлення 🧾")],
    [KeyboardButton("Історія обслуговування 📋")],
]

# Адміністратор - все + спецкоманди
ADMIN_KEYBOARD = [
    [KeyboardButton("Всі замовлення 📦"), KeyboardButton("Всі автомобілі 🚛")],
    [KeyboardButton("Статистика 📊"), KeyboardButton("Пошук авто 🔍")],
]

# Стани для діалогів
AWAITING_TRUCK_SEARCH = 'awaiting_truck_search'


# ============================================================
# ДОПОМІЖНІ ФУНКЦІЇ
# ============================================================

def normalize_phone_number(phone_raw):
    """
    Нормалізує телефонний номер до формату +380XXXXXXXXX
    
    Приклади:
    +380501234567 → +380501234567
    380501234567  → +380501234567
    0501234567    → +380501234567
    8 050 123 45 67 → +380501234567
    """
    # Видаляємо всі нецифрові символи
    clean = re.sub(r'\D', '', phone_raw)
    
    # Перетворюємо в український формат
    if clean.startswith('80') and len(clean) == 11:
        # 80501234567 → +380501234567
        return f'+3{clean}'
    elif clean.startswith('0') and len(clean) == 10:
        # 0501234567 → +380501234567
        return f'+38{clean}'
    elif clean.startswith('380') and len(clean) == 12:
        # 380501234567 → +380501234567
        return f'+{clean}'
    
    # Якщо формат незрозумілий - повертаємо як є
    return phone_raw


def get_keyboard_for_role(role, has_client=False):
    """Повертає клавіатуру відповідно до ролі"""
    # Для гостей перевіряємо чи прив'язаний до клієнта
    if role == 'guest':
        if has_client:
            keyboard = OWNER_KEYBOARD  # Якщо прив'язаний - даємо функції власника
        else:
            keyboard = GUEST_KEYBOARD  # Якщо ні - пропонуємо прив'язатись
    elif role == 'admin':
        keyboard = ADMIN_KEYBOARD
    elif role == 'owner':
        keyboard = OWNER_KEYBOARD
    elif role == 'driver':
        keyboard = DRIVER_KEYBOARD
    else:
        keyboard = GUEST_KEYBOARD
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def safe_send_message(update, text, **kwargs):
    """Безпечна відправка повідомлення з обробкою помилок"""
    try:
        return await update.message.reply_text(text, **kwargs)
    except Forbidden:
        logger.warning(f"User {update.effective_user.id} blocked the bot")
        # Позначаємо користувача як заблокованого
        await sync_to_async(BotUser.objects.filter(
            chat_id=update.effective_user.id
        ).update)(is_blocked=True)
        return None
    except BadRequest as e:
        logger.error(f"Bad request: {e}")
        return None
    except NetworkError as e:
        logger.error(f"Network error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")
        return None


# ============================================================
# ФУНКЦІЇ РОБОТИ З БД
# ============================================================

@sync_to_async
def get_or_create_bot_user(chat_id, username, first_name, last_name=None):
    """
    Отримує або створює користувача бота.
    Якщо користувач новий - створює з роллю 'guest'.
    """
    try:
        bot_user = BotUser.objects.get(chat_id=chat_id)
        # Оновлюємо last_activity
        bot_user.last_activity = timezone.now()
        if bot_user.is_blocked:
            bot_user.is_blocked = False  # Розблоковуємо якщо знову написав
        bot_user.save(update_fields=['last_activity', 'is_blocked'])
        return bot_user, False
    except BotUser.DoesNotExist:
        # Новий користувач - створюємо як гостя
        bot_user = BotUser.objects.create(
            chat_id=chat_id,
            username=username or '',
            first_name=first_name,
            last_name=last_name or '',
            role='guest',
            is_active=True
        )
        logger.info(f"Створено нового користувача-гостя: {chat_id} ({first_name})")
        return bot_user, True


@sync_to_async
def link_user_with_phone(chat_id, phone_number):
    """
    Прив'язує користувача бота до клієнта за номером телефону.
    Якщо клієнт знайдений - змінює роль на 'owner'.
    
    Повертає: (success: bool, message: str)
    """
    try:
        bot_user = BotUser.objects.get(chat_id=chat_id)
    except BotUser.DoesNotExist:
        return False, "Ваш профіль не знайдено. Спробуйте /start"
    
    # Нормалізуємо номер
    normalized_phone = normalize_phone_number(phone_number)
    
    # Зберігаємо номер у профілі
    bot_user.phone_number = normalized_phone
    
    try:
        # Шукаємо клієнта з таким номером
        # Видаляємо + для пошуку
        search_phone = normalized_phone.replace('+', '')
        client = Client.objects.get(phone__contains=search_phone)
        
        # Прив'язуємо
        bot_user.client = client
        bot_user.role = 'owner'
        bot_user.save()
        
        logger.info(f"Користувач {chat_id} прив'язаний до клієнта {client.name}")
        
        return True, (
            f"✅ Успішно!\n\n"
            f"Ваш профіль прив'язано до клієнта:\n"
            f"📋 {client.name}\n"
            f"📞 {client.phone}\n\n"
            f"Тепер ви маєте доступ до всіх ваших автомобілів та замовлень!"
        )
    
    except Client.DoesNotExist:
        # Клієнт не знайдений - залишаємо гостем але зберігаємо номер
        bot_user.save()
        
        return False, (
            f"❌ На жаль, клієнта з номером {normalized_phone} не знайдено в нашій базі.\n\n"
            f"Ваш номер збережено. Зверніться до адміністратора для реєстрації в системі."
        )
    
    except Client.MultipleObjectsReturned:
        bot_user.save()
        
        return False, (
            f"⚠️ Виникла помилка: знайдено декілька клієнтів з номером {normalized_phone}.\n\n"
            f"Будь ласка, зверніться до адміністратора для вирішення."
        )
    
    except Exception as e:
        logger.error(f"Помилка прив'язки користувача {chat_id}: {e}")
        return False, "Виникла невідома помилка. Спробуйте пізніше або зверніться до підтримки."


@sync_to_async
def log_message(chat_id, user_name, message_text, bot_response, phone_number=None):
    """Логування повідомлень"""
    try:
        if not phone_number:
            bot_user = BotUser.objects.filter(chat_id=chat_id).first()
            if bot_user:
                phone_number = bot_user.phone_number
        
        BotMessageLog.objects.create(
            chat_id=chat_id,
            user_name=user_name,
            phone_number=phone_number,
            message_text=message_text,
            bot_response=bot_response
        )
        logger.debug(f"Лог збережено для {chat_id}")
    except Exception as e:
        logger.error(f"Не вдалося зберегти лог для {chat_id}: {e}")


@sync_to_async
def get_user_trucks_with_keyboard(chat_id):
    """
    Отримує список доступних вантажівок для користувача залежно від ролі.
    """
    try:
        bot_user = BotUser.objects.select_related('client').prefetch_related('allowed_trucks').get(chat_id=chat_id)
        
        if not bot_user.is_active:
            return {"reply_text": "❌ Ваш обліковий запис деактивовано. Зверніться до адміністратора.", "keyboard": None}
        
        if bot_user.is_blocked:
            return {"reply_text": "❌ Ваш обліковий запис заблоковано.", "keyboard": None}
        
        trucks = bot_user.get_accessible_trucks()
        
        if not trucks.exists():
            return {"reply_text": "📭 За вами не закріплено жодного автомобіля.", "keyboard": None}

        reply_text = f"🚚 Ваші автомобілі ({trucks.count()} шт.):\n\nОберіть для перегляду історії:"
        
        keyboard = []
        for truck in trucks:
            button = InlineKeyboardButton(
                text=f"🚚 {truck.license_plate} ({truck.specific_model_name})",
                callback_data=f"history_{truck.id}"
            )
            keyboard.append([button])
        
        return {"reply_text": reply_text, "keyboard": InlineKeyboardMarkup(keyboard)}

    except BotUser.DoesNotExist:
        return {"reply_text": "❌ Ваш профіль не знайдено. Використайте /start для реєстрації.", "keyboard": None}
    except Exception as e:
        logger.error(f"Помилка в get_user_trucks_with_keyboard: {e}")
        return {"reply_text": "⚠️ Виникла помилка при отриманні списку автомобілів.", "keyboard": None}


@sync_to_async
def get_repair_history(truck_id, chat_id):
    """
    Отримує історію замовлень для вантажівки.
    Перевіряє права доступу користувача.
    """
    try:
        bot_user = BotUser.objects.select_related('client').get(chat_id=chat_id)
        truck = Truck.objects.select_related('client').get(id=truck_id)
        
        # Перевірка доступу
        if not bot_user.can_view_truck(truck):
            return "❌ У вас немає доступу до цього автомобіля."
        
        orders = ServiceOrder.objects.filter(truck=truck).select_related('client').order_by('-created_at')[:10]
        
        if not orders.exists():
            return f"📭 Для автомобіля {truck.license_plate} ще немає історії ремонтів."

        reply = f"📋 Історія для {truck.license_plate} ({truck.specific_model_name}):\n\n"
        
        for order in orders:
            reply += f"🧾 №{order.order_number or 'б/н'} від {order.created_at.strftime('%d.%m.%Y')}\n"
            reply += f"   Статус: {order.get_status_display()}\n"
            
            # Показуємо вартість тільки власникам та адмінам
            if bot_user.role in ['admin', 'owner']:
                reply += f"   💰 Вартість: {order.total_cost} грн\n"
            
            reply += "\n"

        if orders.count() >= 10:
            reply += "ℹ️ Показано останні 10 записів."
            
        return reply
        
    except BotUser.DoesNotExist:
        return "❌ Ваш профіль не знайдено."
    except Truck.DoesNotExist:
        return "❌ Автомобіль не знайдено."
    except Exception as e:
        logger.error(f"Помилка в get_repair_history: {e}")
        return "⚠️ Не вдалося отримати історію ремонтів."


@sync_to_async
def get_order_info(order_number, chat_id):
    """
    Отримує інформацію про замовлення.
    Для гостей - обмежена інформація.
    """
    try:
        bot_user = BotUser.objects.select_related('client').get(chat_id=chat_id)
        order = ServiceOrder.objects.select_related('client', 'truck').get(order_number=order_number)
        
        # Перевірка доступу (для не-адмінів та не-гостей)
        if bot_user.role not in ['admin', 'guest']:
            if not bot_user.can_view_order(order):
                return "❌ У вас немає доступу до цього замовлення."
        
        reply = f"🧾 Замовлення №{order.order_number}\n"
        reply += f"📊 Статус: {order.get_status_display()}\n"
        
        # Повна інформація для адмінів та власників
        if bot_user.role in ['admin', 'owner']:
            reply += f"👤 Клієнт: {order.client.name if order.client else 'Н/Д'}\n"
            reply += f"🚚 Автомобіль: {order.truck.license_plate if order.truck else 'Н/Д'}\n"
            reply += f"💰 Вартість: {order.total_cost} грн\n"
            if order.problem_description:
                reply += f"📝 Опис: {order.problem_description[:100]}...\n"
        
        # Обмежена інформація для водіїв
        elif bot_user.role == 'driver':
            reply += f"🚚 Автомобіль: {order.truck.license_plate if order.truck else 'Н/Д'}\n"
        
        # Мінімальна інформація для гостей
        # (тільки статус, вже показано вище)
        
        return reply
        
    except BotUser.DoesNotExist:
        return "❌ Ваш профіль не знайдено."
    except ServiceOrder.DoesNotExist:
        return f"❌ Замовлення №{order_number} не знайдено. Перевірте номер."
    except Exception as e:
        logger.error(f"Помилка в get_order_info: {e}")
        return "⚠️ Виникла помилка при отриманні інформації про замовлення."


@sync_to_async
def get_all_orders_for_admin():
    """Отримує останні замовлення (тільки для адміна)"""
    try:
        orders = ServiceOrder.objects.select_related('client', 'truck').order_by('-created_at')[:15]
        
        if not orders.exists():
            return "📭 Замовлень поки що немає."
        
        reply = "📦 Останні 15 замовлень:\n\n"
        
        for order in orders:
            reply += f"🧾 №{order.order_number or 'б/н'}\n"
            reply += f"   📊 {order.get_status_display()}\n"
            reply += f"   👤 {order.client.name if order.client else 'Н/Д'}\n"
            reply += f"   🚚 {order.truck.license_plate if order.truck else 'Н/Д'}\n"
            reply += f"   💰 {order.total_cost} грн\n\n"
        
        return reply
        
    except Exception as e:
        logger.error(f"Помилка в get_all_orders_for_admin: {e}")
        return "⚠️ Помилка отримання списку замовлень."


@sync_to_async
def get_all_trucks_for_admin():
    """Отримує список всіх автомобілів (тільки для адміна)"""
    try:
        trucks = Truck.objects.select_related('client', 'base_model').order_by('license_plate')[:20]
        
        if not trucks.exists():
            return "📭 Автомобілів у базі немає."
        
        reply = f"🚛 Всі автомобілі ({trucks.count()} шт.):\n\n"
        
        for truck in trucks:
            reply += f"🚚 {truck.license_plate}\n"
            reply += f"   Модель: {truck.specific_model_name or 'Н/Д'}\n"
            reply += f"   Власник: {truck.client.name if truck.client else 'Не вказано'}\n"
            
            if truck.client and truck.client.phone:
                reply += f"   📞 {truck.client.phone}\n"
            
            reply += "\n"
        
        if trucks.count() >= 20:
            reply += "ℹ️ Показано перші 20 автомобілів."
        
        return reply
        
    except Exception as e:
        logger.error(f"Помилка в get_all_trucks_for_admin: {e}")
        return "⚠️ Помилка отримання списку автомобілів."


@sync_to_async
def get_bot_stats_for_admin():
    """Статистика бота (тільки для адміна)"""
    try:
        from django.db.models import Count
        
        total_users = BotUser.objects.count()
        active_users = BotUser.objects.filter(is_active=True).count()
        blocked_users = BotUser.objects.filter(is_blocked=True).count()
        
        users_by_role = BotUser.objects.values('role').annotate(count=Count('role'))
        
        reply = "📊 Статистика бота:\n\n"
        reply += f"👥 Всього користувачів: {total_users}\n"
        reply += f"✅ Активних: {active_users}\n"
        reply += f"❌ Заблокованих: {blocked_users}\n\n"
        reply += "📋 По ролях:\n"
        
        role_names = {
            'admin': '👑 Адміністратори',
            'owner': '👤 Власники',
            'driver': '🚗 Водії',
            'guest': '👻 Гості'
        }
        
        for item in users_by_role:
            role_label = role_names.get(item['role'], item['role'])
            reply += f"  {role_label}: {item['count']}\n"
        
        return reply
        
    except Exception as e:
        logger.error(f"Помилка в get_bot_stats_for_admin: {e}")
        return "⚠️ Помилка отримання статистики."


@sync_to_async
def search_truck_by_partial_number(partial_number, chat_id):
    """
    Шукає автомобілі за частковим номером (тільки для адміна).
    Підтримує пошук як по цифрах так і по літерах.
    """
    try:
        bot_user = BotUser.objects.get(chat_id=chat_id)
        
        if bot_user.role != 'admin':
            return "❌ У вас немає доступу до цієї функції."
        
        # Видаляємо всі символи крім літер (українські+англійські) та цифр
        clean_number = re.sub(r'[^A-ZА-ЯІЇЄҐ0-9]', '', partial_number.upper())
        
        if not clean_number:
            return (
                "⚠️ Будь ласка, введіть номер автомобіля.\n\n"
                "Приклади:\n"
                "• AA1234 - знайде AA1234BB, AA1234CC\n"
                "• 1234 - знайде всі номери з цими цифрами\n"
                "• BC5678 - знайде BC5678AA тощо"
            )
        
        # Шукаємо автомобілі де license_plate містить ці символи
        trucks = Truck.objects.filter(
            license_plate__icontains=clean_number
        ).select_related('client')[:20]
        
        if not trucks.exists():
            return f"❌ Автомобілі з '{clean_number}' не знайдено."
        
        reply = f"🔍 Знайдено автомобілів: {trucks.count()}\n\n"
        
        for truck in trucks:
            reply += f"🚚 {truck.license_plate}\n"
            reply += f"   Модель: {truck.specific_model_name or 'Н/Д'}\n"
            reply += f"   Власник: {truck.client.name if truck.client else 'Не вказано'}\n"
            
            if truck.client and truck.client.phone:
                reply += f"   📞 {truck.client.phone}\n"
            
            reply += "\n"
        
        if trucks.count() >= 20:
            reply += "⚠️ Показано перші 20 результатів. Уточніть пошук для меншої кількості збігів."
        
        return reply
        
    except BotUser.DoesNotExist:
        return "❌ Ваш профіль не знайдено."
    except Exception as e:
        logger.error(f"Помилка в search_truck_by_partial_number: {e}")
        return "⚠️ Помилка пошуку автомобілів."


# ============================================================
# ОБРОБНИКИ КОМАНД
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - перевіряє користувача та показує меню"""
    user = update.message.from_user
    chat_id = user.id
    username = user.username or ''
    first_name = user.first_name or 'Користувач'
    last_name = user.last_name or ''
    
    # Скидаємо стан діалогу
    context.user_data['state'] = None
    
    # Отримуємо або створюємо користувача
    bot_user, is_new = await get_or_create_bot_user(chat_id, username, first_name, last_name)
    
    if not bot_user.is_active:
        reply_text = "❌ Ваш обліковий запис деактивовано. Зверніться до адміністратора."
        await safe_send_message(update, reply_text)
        await log_message(chat_id, first_name, "/start", reply_text)
        return
    
    # Вітальне повідомлення залежно від ролі
    role_greetings = {
        'admin': f'👑 Вітаю, адміністраторе {first_name}!\n\nВи маєте повний доступ до всіх функцій системи.',
        'owner': f'👤 Вітаю, {first_name}!\n\nВи можете переглядати інформацію про свої автомобілі та замовлення.',
        'driver': f'🚗 Вітаю, {first_name}!\n\nВи маєте доступ до закріплених за вами автомобілів.',
        'guest': f'👻 Вітаю, {first_name}!\n\nВи можете перевіряти статус замовлень за номером.\n\nДля повного доступу прив\'яжіть свій номер телефону.'
    }
    
    if is_new:
        reply_text = (
            f"Вітаю, {first_name}! 👋\n\n"
            f"Ви зареєстровані як гість.\n"
            f"Ви можете перевіряти статус замовлень за номером.\n\n"
            f"💡 Щоб отримати доступ до своїх автомобілів, натисніть кнопку нижче та поділіться номером телефону."
        )
    else:
        reply_text = role_greetings.get(bot_user.role, f'Вітаю, {first_name}!')
    
    has_client = bot_user.client is not None
    keyboard = get_keyboard_for_role(bot_user.role, has_client)
    
    await safe_send_message(update, reply_text, reply_markup=keyboard)
    await log_message(chat_id, first_name, "/start", reply_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує довідку про доступні команди"""
    user = update.message.from_user
    chat_id = user.id
    first_name = user.first_name or 'Користувач'
    
    # Скидаємо стан
    context.user_data['state'] = None
    
    try:
        bot_user = await sync_to_async(BotUser.objects.get)(chat_id=chat_id)
    except BotUser.DoesNotExist:
        reply_text = "❌ Ваш профіль не знайдено. Використайте /start для реєстрації."
        await safe_send_message(update, reply_text)
        return
    
    # Базова довідка
    reply_text = "📚 Довідка по боту:\n\n"
    reply_text += "🔹 /start - Головне меню\n"
    reply_text += "🔹 /help - Ця довідка\n"
    reply_text += "🔹 /mycars - Мої автомобілі\n\n"
    
    # Додаткова довідка залежно від ролі
    if bot_user.role == 'admin':
        reply_text += "👑 Команди адміністратора:\n"
        reply_text += "• Всі замовлення 📦 - Перегляд усіх замовлень\n"
        reply_text += "• Всі автомобілі 🚛 - Перегляд усіх авто\n"
        reply_text += "• Статистика 📊 - Статистика бота\n"
        reply_text += "• Пошук авто 🔍 - Пошук по номеру\n"
    
    elif bot_user.role == 'owner':
        reply_text += "👤 Ваші можливості:\n"
        reply_text += "• Мої автомобілі 🚚 - Перегляд ваших авто\n"
        reply_text += "• Історія обслуговування 📋 - Історія ремонтів\n"
        reply_text += "• Перевірка замовлення 🧾 - По номеру\n"
    
    elif bot_user.role == 'driver':
        reply_text += "🚗 Ваші можливості:\n"
        reply_text += "• Мої автомобілі 🚚 - Доступні вам авто\n"
        reply_text += "• Перевірка замовлення 🧾 - По номеру\n"
    
    elif bot_user.role == 'guest':
        if bot_user.client:
            reply_text += "👤 Ви прив'язані до клієнта!\n"
            reply_text += "• Мої автомобілі 🚚 - Ваші авто\n"
            reply_text += "• Історія обслуговування 📋\n"
        else:
            reply_text += "👻 Функції гостя:\n"
            reply_text += "• Перевірка замовлення 🧾 - По номеру\n\n"
            reply_text += "💡 Прив'яжіть телефон для доступу до авто!"
    
    await safe_send_message(update, reply_text)
    await log_message(chat_id, first_name, "/help", reply_text)


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє отриманий контакт від користувача.
    Автоматично прив'язує до клієнта якщо знайдено.
    """
    user = update.message.from_user
    chat_id = user.id
    first_name = user.first_name or 'Користувач'
    contact = update.message.contact
    
    # Скидаємо стан
    context.user_data['state'] = None
    
    phone_number = contact.phone_number
    
    logger.info(f"Отримано контакт від {chat_id}: {phone_number}")
    
    # Прив'язуємо користувача
    success, message = await link_user_with_phone(chat_id, phone_number)
    
    # Оновлюємо клавіатуру
    if success:
        # Отримуємо оновленого користувача
        try:
            bot_user = await sync_to_async(BotUser.objects.select_related('client').get)(chat_id=chat_id)
            has_client = bot_user.client is not None
            keyboard = get_keyboard_for_role(bot_user.role, has_client)
        except:
            keyboard = None
    else:
        keyboard = None
    
    await safe_send_message(update, message, reply_markup=keyboard)
    await log_message(chat_id, first_name, f"[Контакт: {phone_number}]", message, phone_number=phone_number)


async def my_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує автомобілі користувача"""
    user = update.message.from_user
    chat_id = user.id
    first_name = user.first_name or 'Користувач'
    message_text = update.message.text
    
    # Скидаємо стан
    context.user_data['state'] = None

    result = await get_user_trucks_with_keyboard(chat_id)
    reply_text = result.get("reply_text")
    keyboard = result.get("keyboard")

    await safe_send_message(update, reply_text, reply_markup=keyboard)
    await log_message(chat_id, first_name, message_text, reply_text)


async def ask_for_order_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просить ввести номер замовлення"""
    user = update.message.from_user
    chat_id = user.id
    first_name = user.first_name or 'Користувач'
    message_text = update.message.text
    
    # Скидаємо стан
    context.user_data['state'] = None
    
    reply_text = "🔢 Будь ласка, надішліть номер замовлення-наряду.\n\nНаприклад: 12345"
    
    await safe_send_message(update, reply_text)
    await log_message(chat_id, first_name, message_text, reply_text)


async def show_all_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує всі замовлення (тільки для адміна)"""
    user = update.message.from_user
    chat_id = user.id
    first_name = user.first_name or 'Користувач'
    
    # Скидаємо стан
    context.user_data['state'] = None
    
    # Перевірка прав
    try:
        bot_user = await sync_to_async(BotUser.objects.get)(chat_id=chat_id)
        if bot_user.role != 'admin':
            reply_text = "❌ У вас немає доступу до цієї функції."
            await safe_send_message(update, reply_text)
            return
    except BotUser.DoesNotExist:
        reply_text = "❌ Ваш профіль не знайдено."
        await safe_send_message(update, reply_text)
        return
    
    reply_text = await get_all_orders_for_admin()
    await safe_send_message(update, reply_text)
    await log_message(chat_id, first_name, "Всі замовлення 📦", reply_text)


async def show_all_trucks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує всі автомобілі (тільки для адміна)"""
    user = update.message.from_user
    chat_id = user.id
    first_name = user.first_name or 'Користувач'
    
    # Скидаємо стан
    context.user_data['state'] = None
    
    # Перевірка прав
    try:
        bot_user = await sync_to_async(BotUser.objects.get)(chat_id=chat_id)
        if bot_user.role != 'admin':
            reply_text = "❌ У вас немає доступу до цієї функції."
            await safe_send_message(update, reply_text)
            return
    except BotUser.DoesNotExist:
        reply_text = "❌ Ваш профіль не знайдено."
        await safe_send_message(update, reply_text)
        return
    
    reply_text = await get_all_trucks_for_admin()
    await safe_send_message(update, reply_text)
    await log_message(chat_id, first_name, "Всі автомобілі 🚛", reply_text)


async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує статистику (тільки для адміна)"""
    user = update.message.from_user
    chat_id = user.id
    first_name = user.first_name or 'Користувач'
    
    # Скидаємо стан
    context.user_data['state'] = None
    
    # Перевірка прав
    try:
        bot_user = await sync_to_async(BotUser.objects.get)(chat_id=chat_id)
        if bot_user.role != 'admin':
            reply_text = "❌ У вас немає доступу до цієї функції."
            await safe_send_message(update, reply_text)
            return
    except BotUser.DoesNotExist:
        reply_text = "❌ Ваш профіль не знайдено."
        await safe_send_message(update, reply_text)
        return
    
    reply_text = await get_bot_stats_for_admin()
    await safe_send_message(update, reply_text)
    await log_message(chat_id, first_name, "Статистика 📊", reply_text)


async def ask_for_truck_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просить адміна ввести номер/частину номера автомобіля"""
    user = update.message.from_user
    chat_id = user.id
    first_name = user.first_name or 'Користувач'
    
    # Перевірка прав
    try:
        bot_user = await sync_to_async(BotUser.objects.get)(chat_id=chat_id)
        if bot_user.role != 'admin':
            reply_text = "❌ У вас немає доступу до цієї функції."
            await safe_send_message(update, reply_text)
            return
    except BotUser.DoesNotExist:
        reply_text = "❌ Ваш профіль не знайдено."
        await safe_send_message(update, reply_text)
        return
    
    # Встановлюємо стан очікування
    context.user_data['state'] = AWAITING_TRUCK_SEARCH
    
    reply_text = (
        "🔍 Введіть номер або частину номера автомобіля.\n\n"
        "Приклади:\n"
        "• AA1234 - знайде AA1234BB, AA1234CC\n"
        "• 1234 - знайде всі номери з цими цифрами\n"
        "• BC5678 - знайде BC5678AA тощо\n\n"
        "ℹ️ Для скасування натисніть будь-яку кнопку меню."
    )
    
    await safe_send_message(update, reply_text)
    await log_message(chat_id, first_name, "Пошук авто 🔍", reply_text)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє текстові повідомлення"""
    user = update.message.from_user
    chat_id = user.id
    first_name = user.first_name or 'Користувач'
    original_text = update.message.text
    
    # Перевіряємо чи очікуємо введення номера авто
    if context.user_data.get('state') == AWAITING_TRUCK_SEARCH:
        # Скидаємо стан
        context.user_data['state'] = None
        
        # Шукаємо авто
        reply_message = await search_truck_by_partial_number(original_text, chat_id)
        await safe_send_message(update, reply_message)
        await log_message(chat_id, first_name, f"[Пошук: {original_text}]", reply_message)
        return
    
    # Інакше припускаємо що це номер замовлення
    order_number = re.sub(r'\D', '', original_text)
    
    if not order_number:
        reply_message = "❓ Вибачте, я не зрозумів.\n\nОберіть опцію з меню або надішліть номер замовлення."
        await safe_send_message(update, reply_message)
        await log_message(chat_id, first_name, original_text, reply_message)
        return

    reply_message = await get_order_info(order_number, chat_id)
    await safe_send_message(update, reply_message)
    await log_message(chat_id, first_name, original_text, reply_message)


async def handle_car_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє вибір автомобіля з inline клавіатури"""
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    chat_id = query.message.chat.id
    first_name = query.from_user.first_name or 'Користувач'
    
    try:
        action, truck_id = callback_data.split('_')
        
        if action == 'history':
            reply_text = await get_repair_history(int(truck_id), chat_id)
            
            try:
                await query.edit_message_text(text=reply_text)
            except BadRequest as e:
                # Повідомлення не змінилось або інша помилка
                logger.warning(f"Cannot edit message: {e}")
            
            await log_message(chat_id, first_name, f"[История авто {truck_id}]", reply_text)
        else:
            await query.edit_message_text(text="❌ Невідома дія.")

    except Exception as e:
        logger.error(f"Помилка обробки callback: {e}")
        try:
            await query.edit_message_text(text="⚠️ Сталася помилка при обробці вашого запиту.")
        except:
            pass


# ============================================================
# DJANGO MANAGEMENT COMMAND
# ============================================================

class Command(BaseCommand):
    help = 'Запускає Telegram бота з системою ролей та прив\'язкою телефонів'

    def handle(self, *args, **options):
        if not BOT_TOKEN:
            logger.error("❌ ПОМИЛКА: Змінна оточення TELEGRAM_BOT_TOKEN не встановлена!")
            return

        self.stdout.write(self.style.SUCCESS('🤖 Бот запускається...'))

        application = Application.builder().token(BOT_TOKEN).build()

        # ⚡ ПОРЯДОК ОБРОБНИКІВ КРИТИЧНО ВАЖЛИВИЙ! ⚡
        
        # 1. КОМАНДИ (мають найвищий пріоритет)
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("mycars", my_cars))
        
        # 2. КОНТАКТИ (ОБОВ'ЯЗКОВО ДО filters.TEXT!)
        application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
        
        # 3. КНОПКИ МЕНЮ (Regex patterns)
        application.add_handler(MessageHandler(filters.Regex("^Мої автомобілі 🚚$"), my_cars))
        application.add_handler(MessageHandler(filters.Regex("^Перевірити статус замовлення 🧾$"), ask_for_order_number))
        application.add_handler(MessageHandler(filters.Regex("^Історія обслуговування 📋$"), my_cars))
        
        # Адмін-кнопки
        application.add_handler(MessageHandler(filters.Regex("^Всі замовлення 📦$"), show_all_orders))
        application.add_handler(MessageHandler(filters.Regex("^Всі автомобілі 🚛$"), show_all_trucks))
        application.add_handler(MessageHandler(filters.Regex("^Статистика 📊$"), show_statistics))
        application.add_handler(MessageHandler(filters.Regex("^Пошук авто 🔍$"), ask_for_truck_number))
        
        # 4. INLINE КНОПКИ (Callbacks)
        application.add_handler(CallbackQueryHandler(handle_car_selection, pattern='^history_'))
        
        # 5. ВЕСЬ ІНШИЙ ТЕКСТ (ЗАВЖДИ ОСТАННІМ!)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

        try:
            self.stdout.write(self.style.SUCCESS('✅ Бот успішно запущено!'))
            self.stdout.write(self.style.SUCCESS('📋 Функції:'))
            self.stdout.write('   • Система ролей (admin/owner/driver/guest)')
            self.stdout.write('   • Автоматична прив\'язка по номеру телефону')
            self.stdout.write('   • Пошук авто по літерах та цифрах')
            self.stdout.write('   • Обробка помилок Telegram API')
            self.stdout.write('   • Команди /start, /help, /mycars')
            application.run_polling()
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('🛑 Бот зупинено.'))
        except Exception as e:
            logger.error(f"❌ Бот впав з помилкою: {e}")
            raise e