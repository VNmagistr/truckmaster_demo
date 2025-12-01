import os
import logging
import asyncio
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
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
    [KeyboardButton("Створити замовлення ➕"), KeyboardButton("Логи бота 📝")],
]

# Стани для діалогів
AWAITING_TRUCK_SEARCH = 'awaiting_truck_search'


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
        bot_user.save(update_fields=['last_activity'])
        return bot_user, False
    except BotUser.DoesNotExist:
        # Новий користувач - створюємо як гостя
        bot_user = BotUser.objects.create(
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            last_name=last_name or '',
            role='guest',
            is_active=True
        )
        logger.info(f"Створено нового користувача-гостя: {chat_id} ({first_name})")
        return bot_user, True


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
        logger.info(f"Лог збережено для {chat_id}")
    except Exception as e:
        logger.error(f"Не вдалося зберегти лог для {chat_id}: {e}")


@sync_to_async
def get_user_trucks_with_keyboard(chat_id):
    """
    Отримує список доступних вантажівок для користувача залежно від ролі.
    """
    try:
        bot_user = BotUser.objects.get(chat_id=chat_id)
        
        if not bot_user.is_active:
            return {"reply_text": "Ваш обліковий запис деактивовано. Зверніться до адміністратора.", "keyboard": None}
        
        if bot_user.is_blocked:
            return {"reply_text": "Ваш обліковий запис заблоковано.", "keyboard": None}
        
        trucks = bot_user.get_accessible_trucks()
        
        if not trucks:
            return {"reply_text": "За вами не закріплено жодного автомобіля.", "keyboard": None}

        reply_text = "Ваші автомобілі. Оберіть для перегляду історії:"
        
        keyboard = []
        for truck in trucks:
            button = InlineKeyboardButton(
                text=f"🚚 {truck.license_plate} ({truck.specific_model_name})",
                callback_data=f"history_{truck.id}"
            )
            keyboard.append([button])
        
        return {"reply_text": reply_text, "keyboard": InlineKeyboardMarkup(keyboard)}

    except BotUser.DoesNotExist:
        return {"reply_text": "Ваш профіль не знайдено. Використайте /start для реєстрації.", "keyboard": None}
    except Exception as e:
        logger.error(f"Помилка в get_user_trucks_with_keyboard: {e}")
        return {"reply_text": "Виникла помилка при отриманні списку автомобілів.", "keyboard": None}


@sync_to_async
def get_repair_history(truck_id, chat_id):
    """
    Отримує історію замовлень для вантажівки.
    Перевіряє права доступу користувача.
    """
    try:
        bot_user = BotUser.objects.get(chat_id=chat_id)
        truck = Truck.objects.get(id=truck_id)
        
        # Перевірка доступу
        if not bot_user.can_view_truck(truck):
            return "У вас немає доступу до цього автомобіля."
        
        orders = ServiceOrder.objects.filter(truck=truck).order_by('-created_at')
        
        if not orders.exists():
            return f"Для автомобіля {truck.license_plate} ще немає історії ремонтів."

        reply = f"📋 Історія для {truck.license_plate} ({truck.specific_model_name}):\n\n"
        
        for order in orders[:5]:
            reply += f"🧾 №{order.order_number or 'б/н'} від {order.created_at.strftime('%d.%m.%Y')}\n"
            reply += f"   Статус: {order.get_status_display()}\n"
            
            # Показуємо вартість тільки власникам та адмінам
            if bot_user.role in ['admin', 'owner']:
                reply += f"   Вартість: {order.total_cost} грн\n"
            
            reply += "\n"

        if orders.count() > 5:
            reply += f"...та ще {orders.count() - 5} записів."
            
        return reply
        
    except BotUser.DoesNotExist:
        return "Ваш профіль не знайдено."
    except Truck.DoesNotExist:
        return "Автомобіль не знайдено."
    except Exception as e:
        logger.error(f"Помилка в get_repair_history: {e}")
        return "Не вдалося отримати історію ремонтів."


@sync_to_async
def get_order_info(order_number, chat_id):
    """
    Отримує інформацію про замовлення.
    Для гостей - обмежена інформація.
    """
    try:
        bot_user = BotUser.objects.get(chat_id=chat_id)
        order = ServiceOrder.objects.select_related('client', 'truck').get(order_number=order_number)
        
        # Перевірка доступу (для не-адмінів та не-гостей)
        if bot_user.role not in ['admin', 'guest']:
            if not bot_user.can_view_order(order):
                return "У вас немає доступу до цього замовлення."
        
        reply = f"🧾 Замовлення №{order.order_number}\n"
        reply += f"Статус: {order.get_status_display()}\n"
        
        # Повна інформація для адмінів та власників
        if bot_user.role in ['admin', 'owner']:
            reply += f"Клієнт: {order.client.name if order.client else 'Н/Д'}\n"
            reply += f"Автомобіль: {order.truck.license_plate if order.truck else 'Н/Д'}\n"
            reply += f"Вартість: {order.total_cost} грн\n"
            if order.problem_description:
                reply += f"Опис: {order.problem_description}\n"
        
        # Обмежена інформація для водіїв
        elif bot_user.role == 'driver':
            reply += f"Автомобіль: {order.truck.license_plate if order.truck else 'Н/Д'}\n"
        
        # Мінімальна інформація для гостей
        # (тільки статус, вже показано вище)
        
        return reply
        
    except BotUser.DoesNotExist:
        return "Ваш профіль не знайдено."
    except ServiceOrder.DoesNotExist:
        return f"Замовлення №{order_number} не знайдено. Перевірте номер."
    except Exception as e:
        logger.error(f"Помилка в get_order_info: {e}")
        return "Виникла помилка при отриманні інформації про замовлення."


@sync_to_async
def get_all_orders_for_admin():
    """Отримує останні замовлення (тільки для адміна)"""
    try:
        orders = ServiceOrder.objects.select_related('client', 'truck').order_by('-created_at')[:10]
        
        if not orders:
            return "Замовлень поки що немає."
        
        reply = "📦 Останні 10 замовлень:\n\n"
        
        for order in orders:
            reply += f"🧾 №{order.order_number or 'б/н'}\n"
            reply += f"   {order.get_status_display()}\n"
            reply += f"   {order.client.name if order.client else 'Н/Д'}\n"
            reply += f"   {order.truck.license_plate if order.truck else 'Н/Д'}\n"
            reply += f"   {order.total_cost} грн\n\n"
        
        return reply
        
    except Exception as e:
        logger.error(f"Помилка в get_all_orders_for_admin: {e}")
        return "Помилка отримання списку замовлень."


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
        reply += f"Всього користувачів: {total_users}\n"
        reply += f"Активних: {active_users}\n"
        reply += f"Заблокованих: {blocked_users}\n\n"
        reply += "По ролях:\n"
        
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
        return "Помилка отримання статистики."


@sync_to_async
def search_truck_by_partial_number(partial_number, chat_id):
    """
    Шукає автомобілі за частковим номером (тільки для адміна).
    """
    try:
        bot_user = BotUser.objects.get(chat_id=chat_id)
        
        if bot_user.role != 'admin':
            return "У вас немає доступу до цієї функції."
        
        # Видаляємо всі не-цифри з введеного тексту
        digits_only = re.sub(r'\D', '', partial_number)
        
        if not digits_only:
            return "Будь ласка, введіть цифри з номера автомобіля.\nНаприклад: 1234"
        
        # Шукаємо автомобілі де license_plate містить ці цифри
        trucks = Truck.objects.filter(
            license_plate__icontains=digits_only
        ).select_related('client')[:20]  # Обмежуємо до 20 результатів
        
        if not trucks.exists():
            return f"Автомобілі з цифрами '{digits_only}' не знайдено."
        
        reply = f"🔍 Знайдено автомобілів: {trucks.count()}\n\n"
        
        for truck in trucks:
            reply += f"🚚 {truck.license_plate}\n"
            reply += f"   Модель: {truck.specific_model_name or 'Н/Д'}\n"
            reply += f"   Власник: {truck.client.name if truck.client else 'Не вказано'}\n"
            
            if truck.client and truck.client.phone:
                reply += f"   Телефон: {truck.client.phone}\n"
            
            reply += "\n"
        
        if trucks.count() >= 20:
            reply += "⚠️ Показано перші 20 результатів. Уточніть пошук для меншої кількості збігів."
        
        return reply
        
    except BotUser.DoesNotExist:
        return "Ваш профіль не знайдено."
    except Exception as e:
        logger.error(f"Помилка в search_truck_by_partial_number: {e}")
        return "Помилка пошуку автомобілів."


def get_keyboard_for_role(role):
    """Повертає клавіатуру відповідно до ролі"""
    keyboards = {
        'admin': ADMIN_KEYBOARD,
        'owner': OWNER_KEYBOARD,
        'driver': DRIVER_KEYBOARD,
        'guest': GUEST_KEYBOARD,
    }
    keyboard = keyboards.get(role, GUEST_KEYBOARD)
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


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
        reply_text = "Ваш обліковий запис деактивовано. Зверніться до адміністратора."
        await update.message.reply_text(reply_text)
        await log_message(chat_id, first_name, "/start", reply_text)
        return
    
    if bot_user.is_blocked:
        reply_text = "Ваш обліковий запис заблоковано."
        await update.message.reply_text(reply_text)
        await log_message(chat_id, first_name, "/start", reply_text)
        return
    
    # Вітальне повідомлення залежно від ролі
    role_greetings = {
        'admin': f'👑 Вітаю, адміністраторе {first_name}!\n\nВи маєте повний доступ до всіх функцій.',
        'owner': f'👤 Вітаю, {first_name}!\n\nВи можете переглядати інформацію про свої автомобілі та замовлення.',
        'driver': f'🚗 Вітаю, {first_name}!\n\nВи маєте доступ до закріплених за вами автомобілів.',
        'guest': f'👻 Вітаю, {first_name}!\n\nВи можете перевіряти статус замовлень за номером.\n\nДля повного доступу зверніться до адміністратора.'
    }
    
    if is_new:
        reply_text = (
            f"Вітаю, {first_name}! 👋\n\n"
            f"Ви зареєстровані як гість.\n"
            f"Ви можете перевіряти статус замовлень за номером.\n\n"
            f"Для отримання повного доступу зверніться до адміністратора."
        )
    else:
        reply_text = role_greetings.get(bot_user.role, f'Вітаю, {first_name}!')
    
    keyboard = get_keyboard_for_role(bot_user.role)
    await update.message.reply_text(reply_text, reply_markup=keyboard)
    await log_message(chat_id, first_name, "/start", reply_text)


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

    await update.message.reply_text(reply_text, reply_markup=keyboard)
    await log_message(chat_id, first_name, message_text, reply_text)


async def ask_for_order_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просить ввести номер замовлення"""
    user = update.message.from_user
    chat_id = user.id
    first_name = user.first_name or 'Користувач'
    message_text = update.message.text
    
    # Скидаємо стан
    context.user_data['state'] = None
    
    reply_text = "Будь ласка, надішліть номер замовлення-наряду."
    
    await update.message.reply_text(reply_text)
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
            reply_text = "У вас немає доступу до цієї функції."
            await update.message.reply_text(reply_text)
            return
    except BotUser.DoesNotExist:
        reply_text = "Ваш профіль не знайдено."
        await update.message.reply_text(reply_text)
        return
    
    reply_text = await get_all_orders_for_admin()
    await update.message.reply_text(reply_text)
    await log_message(chat_id, first_name, "Всі замовлення 📦", reply_text)


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
            reply_text = "У вас немає доступу до цієї функції."
            await update.message.reply_text(reply_text)
            return
    except BotUser.DoesNotExist:
        reply_text = "Ваш профіль не знайдено."
        await update.message.reply_text(reply_text)
        return
    
    reply_text = await get_bot_stats_for_admin()
    await update.message.reply_text(reply_text)
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
            reply_text = "У вас немає доступу до цієї функції."
            await update.message.reply_text(reply_text)
            return
    except BotUser.DoesNotExist:
        reply_text = "Ваш профіль не знайдено."
        await update.message.reply_text(reply_text)
        return
    
    # Встановлюємо стан очікування
    context.user_data['state'] = AWAITING_TRUCK_SEARCH
    
    reply_text = (
        "🔍 Введіть цифри з номера автомобіля.\n\n"
        "Наприклад:\n"
        "• 1234 - знайде АА1234ВВ, ВС1234АА і т.д.\n"
        "• 5678 - знайде всі номери з цими цифрами\n\n"
        "Для скасування натисніть будь-яку кнопку меню."
    )
    
    await update.message.reply_text(reply_text)
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
        await update.message.reply_text(reply_message)
        await log_message(chat_id, first_name, f"[Пошук авто: {original_text}]", reply_message)
        return
    
    # Інакше припускаємо що це номер замовлення
    order_number = re.sub(r'\D', '', original_text)
    
    if not order_number:
        reply_message = "Вибачте, я не зрозумів. Оберіть опцію з меню або надішліть номер замовлення."
        await update.message.reply_text(reply_message)
        await log_message(chat_id, first_name, original_text, reply_message)
        return

    reply_message = await get_order_info(order_number, chat_id)
    await update.message.reply_text(reply_message)
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
            await query.edit_message_text(text=reply_text)
            await log_message(chat_id, first_name, f"[Перегляд історії авто {truck_id}]", reply_text)
        else:
            await query.edit_message_text(text="Невідома дія.")

    except Exception as e:
        logger.error(f"Помилка обробки callback: {e}")
        await query.edit_message_text(text="Сталася помилка при обробці вашого запиту.")


# ============================================================
# DJANGO MANAGEMENT COMMAND
# ============================================================

class Command(BaseCommand):
    help = 'Запускає Telegram бота з системою ролей'

    def handle(self, *args, **options):
        if not BOT_TOKEN:
            logger.error("ПОМИЛКА: Змінна оточення TELEGRAM_BOT_TOKEN не встановлена!")
            return

        self.stdout.write(self.style.SUCCESS('🤖 Бот запускається з системою ролей...'))

        application = Application.builder().token(BOT_TOKEN).build()

        # Команди
        application.add_handler(CommandHandler("start", start))
        
        # Кнопки меню
        application.add_handler(MessageHandler(filters.Regex("^Мої автомобілі 🚚$"), my_cars))
        application.add_handler(MessageHandler(filters.Regex("^Перевірити статус замовлення 🧾$"), ask_for_order_number))
        application.add_handler(MessageHandler(filters.Regex("^Історія обслуговування 📋$"), my_cars))
        
        # Адмін-кнопки
        application.add_handler(MessageHandler(filters.Regex("^Всі замовлення 📦$"), show_all_orders))
        application.add_handler(MessageHandler(filters.Regex("^Статистика 📊$"), show_statistics))
        application.add_handler(MessageHandler(filters.Regex("^Пошук авто 🔍$"), ask_for_truck_number))
        
        # Inline кнопки
        application.add_handler(CallbackQueryHandler(handle_car_selection, pattern='^history_'))
        
        # Текстові повідомлення
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

        try:
            self.stdout.write(self.style.SUCCESS('✅ Бот запущено! Система ролей активна.'))
            application.run_polling()
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('🛑 Бот зупинено.'))
        except Exception as e:
            logger.error(f"Бот впав з помилкою: {e}")
            raise e