import io
import os
import logging
import asyncio
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from orders.models import ServiceOrder, RepairPhoto
from clients.models import Client, Truck
from bot.models import BotUser, BotMessageLog
from asgiref.sync import sync_to_async
from django.db.models import Q

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
logger = logging.getLogger(__name__)

# --- 1. Клавіатури ---
MAIN_KEYBOARD = [
    [KeyboardButton("Мої автомобілі 🚚")],
    [KeyboardButton("Перевірити статус замовлення 🧾")],
    [KeyboardButton("🔔 Нагадування")],
]
MAIN_REPLY_MARKUP = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)

ADMIN_KEYBOARD = [
    [KeyboardButton("Мої автомобілі 🚚"), KeyboardButton("Всі автомобілі 🚛")],
    [KeyboardButton("Перевірити статус замовлення 🧾"), KeyboardButton("Всі замовлення 📋")],
    [KeyboardButton("Знайти авто за номером 🔍"), KeyboardButton("Знайти клієнта 👤")],
    [KeyboardButton("📷 Фото замовлення"), KeyboardButton("Статистика 📊")],
]
ADMIN_REPLY_MARKUP = ReplyKeyboardMarkup(ADMIN_KEYBOARD, resize_keyboard=True)

# --- 1.5 Клавіатура вибору типу фото ---

def get_photo_type_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📷 Номерний знак", callback_data="photo_type_car"),
            InlineKeyboardButton("🔢 Одометр", callback_data="photo_type_odometer"),
        ],
        [
            InlineKeyboardButton("🎛 Панель приладів", callback_data="photo_type_dashboard"),
            InlineKeyboardButton("🔧 Фото ремонту", callback_data="photo_type_repair"),
        ],
        [InlineKeyboardButton("❌ Скасувати", callback_data="photo_cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_order_selection_keyboard(orders):
    """Inline-клавіатура з переліком знайдених замовлень для вибору."""
    keyboard = []
    for order in orders:
        plate = order.truck.license_plate if order.truck else '—'
        date = order.created_at.strftime('%d.%m.%y')
        label = f"№{order.order_number}  {plate}  {date}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"photo_order_{order.id}")])
    keyboard.append([InlineKeyboardButton("❌ Скасувати", callback_data="photo_cancel")])
    return InlineKeyboardMarkup(keyboard)


# --- 2. Допоміжні функції ---
@sync_to_async
def get_or_create_bot_user(telegram_user):
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
        if not created:
            updated = False
            if bot_user.username != (telegram_user.username or ''):
                bot_user.username = telegram_user.username or ''
                updated = True
            if bot_user.first_name != (telegram_user.first_name or ''):
                bot_user.first_name = telegram_user.first_name or ''
                updated = True
            if updated:
                bot_user.save()
        return bot_user
    except Exception as e:
        logger.error(f"Помилка get_or_create_bot_user: {e}")
        return None

@sync_to_async
def check_if_user_is_linked(telegram_id):
    try:
        bot_user = BotUser.objects.select_related('client').get(telegram_id=telegram_id)
        # Перевіряємо тільки наявність КЛІЄНТА (механіків ігноруємо)
        is_linked = bot_user.client is not None
        is_admin = bot_user.role == 'admin'
        return is_linked, is_admin, bot_user
    except BotUser.DoesNotExist:
        return False, False, None

@sync_to_async
def link_bot_user_by_phone(bot_user, phone_number):
    try:
        clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')[-9:]
        
        # Шукаємо ТІЛЬКИ серед Клієнтів
        client = Client.objects.filter(phone__contains=clean_phone).first()
        
        if not client:
            return (
                f"Дякую, {bot_user.first_name}! На жаль, я не знайшов КЛІЄНТА з номером {phone_number}. "
                "Якщо ви механік - цей бот не для вас. Якщо клієнт - зверніться до менеджера."
            )
        
        # Прив'язуємо
        bot_user.client = client
        bot_user.phone_number = phone_number
        
        if client.is_admin:
            bot_user.role = 'admin'
        elif client.truck_set.exists():
            bot_user.role = 'owner'
        else:
            bot_user.role = 'guest'
        
        bot_user.assigned_trucks.set(client.truck_set.all())
        bot_user.save()
        
        return f"Вітаю! Ваш профіль клієнта '{client.name}' успішно прив'язано."

    except Exception as e:
        logger.error(f"Помилка прив'язки: {e}")
        return "Виникла помилка. Спробуйте пізніше."

@sync_to_async
def log_message_to_db(bot_user, message_text, bot_response, message_type='text', is_incoming=True):
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
        logger.error(f"Log error: {e}")

@sync_to_async
def get_my_cars_with_keyboard(bot_user):
    if not bot_user.client:
        return {"reply_text": "Ви не авторизовані як клієнт.", "keyboard": None}
    
    trucks = bot_user.assigned_trucks.all()
    if not trucks.exists():
        return {"reply_text": "За вами не закріплено авто.", "keyboard": None}

    reply_text = "Ваші автомобілі:"
    keyboard = []
    for truck in trucks:
        button = InlineKeyboardButton(
            text=f"🚚 {truck.license_plate} ({truck.specific_model_name})",
            callback_data=f"history_{truck.id}"
        )
        keyboard.append([button])
    
    return {"reply_text": reply_text, "keyboard": InlineKeyboardMarkup(keyboard)}

# --- АДМІН ФУНКЦІЇ (Залишаємо як є, вони працюють через Client.is_admin) ---
@sync_to_async
def get_all_trucks():
    trucks = Truck.objects.select_related('client').all()[:10]
    if not trucks: return "Немає даних."
    reply = "📋 Всі авто (топ 10):\n"
    for t in trucks:
        reply += f"🚚 {t.license_plate} ({t.specific_model_name}) - {t.client.name if t.client else '---'}\n"
    return reply

@sync_to_async
def get_all_orders():
    # Використовуємо нові поля ServiceOrder
    orders = ServiceOrder.objects.select_related('client', 'truck').order_by('-created_at')[:10]
    if not orders: return "Немає замовлень."
    reply = "📋 Останні замовлення:\n"
    for o in orders:
        reply += f"🧾 №{o.order_number} | {o.truck.license_plate if o.truck else '-'} | {o.get_status_display()}\n"
    return reply

@sync_to_async
def get_statistics():
    from django.db.models import Count
    total_clients = Client.objects.count()
    total_trucks = Truck.objects.count()
    total_orders = ServiceOrder.objects.count()
    return f"📊 Статистика:\nКлієнтів: {total_clients}\nАвто: {total_trucks}\nЗамовлень: {total_orders}"

@sync_to_async
def find_truck_by_plate(plate):
    clean = plate.strip().upper().replace(' ','')
    trucks = Truck.objects.filter(license_plate__icontains=clean).select_related('client')
    if not trucks: return "Не знайдено."
    reply = ""
    for t in trucks[:5]:
        reply += f"🚚 {t.license_plate} ({t.specific_model_name})\nВласник: {t.client.name if t.client else '-'}\n\n"
    return reply

@sync_to_async
def find_client_by_name(name):
    clients = Client.objects.filter(name__icontains=name.strip())[:5]
    if not clients: return "Не знайдено."
    reply = ""
    for c in clients:
        reply += f"👤 {c.name} ({c.phone or '-'})\n"
    return reply

@sync_to_async
def save_mileage_report(bot_user, truck_id, mileage):
    """Зберігає введений пробіг і повертає (truck, повідомлення)."""
    from bot.models import MileageReport
    truck = Truck.objects.get(id=truck_id)
    MileageReport.objects.create(bot_user=bot_user, truck=truck, mileage=mileage)
    formatted = f"{mileage:,}".replace(",", " ")
    reply = (
        f"✅ Пробіг *{formatted} км* для *{truck.license_plate}* збережено. Дякуємо!\n\n"
        "Ми повідомимо вас коли підійде час технічного обслуговування."
    )
    return truck, reply


@sync_to_async
def get_client_reminders(bot_user):
    """Повертає активні нагадування для всіх вантажівок клієнта."""
    from maintenance.models import ServiceReminder
    from django.utils import timezone

    if not bot_user.client:
        return []

    trucks = list(bot_user.assigned_trucks.all())
    if not trucks:
        return []

    reminders = list(
        ServiceReminder.objects.filter(
            truck__in=trucks,
            status__in=['pending', 'notified', 'overdue'],
        ).select_related('truck').order_by('status', 'target_mileage', 'target_date')
    )

    today = timezone.now().date()
    result = []
    for r in reminders:
        current_mileage = r.truck.get_latest_mileage()
        km_left = (r.target_mileage - current_mileage) if r.target_mileage and current_mileage else None
        days_left = (r.target_date - today).days if r.target_date else None
        result.append({
            'title': r.title,
            'plate': r.truck.license_plate,
            'status': r.status,
            'km_left': km_left,
            'days_left': days_left,
            'target_mileage': r.target_mileage,
            'current_mileage': current_mileage,
        })

    return result


@sync_to_async
def get_orders_for_photo(query):
    """Повертає список замовлень за точним або частковим збігом номера."""
    query = query.strip()
    exact = ServiceOrder.objects.filter(order_number=query).select_related('truck')
    if exact.exists():
        return list(exact[:1])
    return list(
        ServiceOrder.objects.filter(order_number__endswith=query)
        .select_related('truck')
        .order_by('-created_at')[:10]
    )


@sync_to_async
def save_order_photo(order_id, photo_type, photo_bytes, filename):
    """Зберігає фото номерного знаку, одометра або панелі до полів ServiceOrder."""
    order = ServiceOrder.objects.get(id=order_id)
    content = ContentFile(photo_bytes, name=filename)
    field_map = {
        'car': 'car_photo',
        'odometer': 'odometer_photo',
        'dashboard': 'dashboard_photo',
    }
    field_name = field_map[photo_type]
    getattr(order, field_name).save(filename, content, save=True)


@sync_to_async
def save_repair_photo(order_id, photo_bytes, filename):
    """Створює новий запис RepairPhoto для фото ремонту."""
    order = ServiceOrder.objects.get(id=order_id)
    repair_photo = RepairPhoto(service_order=order)
    repair_photo.image.save(filename, ContentFile(photo_bytes, name=filename), save=True)


@sync_to_async
def get_repair_history(truck_id):
    try:
        truck = Truck.objects.get(id=truck_id)
        orders = ServiceOrder.objects.filter(truck=truck).order_by('-created_at')[:5]
        if not orders: return "Історії немає."
        reply = f"Історія {truck.license_plate}:\n"
        for o in orders:
            reply += f"🔹 {o.created_at.strftime('%d.%m.%y')} - {o.get_status_display()}\n"
        return reply
    except: return "Помилка."

@sync_to_async
def get_order_status(order_number):
    try:
        order = ServiceOrder.objects.select_related('client', 'truck').get(order_number=order_number.strip())
        text = f"📝 *Замовлення №{order.order_number}*\n\n"
        text += f"📊 Статус: *{order.get_status_display()}*\n"
        text += f"📅 Дата: {order.created_at.strftime('%d.%m.%Y')}\n"
        if order.truck:
            truck_info = order.truck.license_plate
            if order.truck.specific_model_name:
                truck_info += f" ({order.truck.specific_model_name})"
            text += f"🚚 Авто: {truck_info}\n"
        if order.client:
            text += f"👤 Клієнт: {order.client.name}\n"
        if order.problem_description:
            text += f"📋 Опис: {order.problem_description[:200]}\n"
        if order.total_cost:
            text += f"💰 Вартість: {order.total_cost} грн\n"
        return text
    except ServiceOrder.DoesNotExist:
        return f"❌ Замовлення #{order_number} не знайдено."

# --- 3. ОБРОБНИКИ (Handlers) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    bot_user = await get_or_create_bot_user(user)
    is_linked, is_admin, _ = await check_if_user_is_linked(user.id)

    if is_linked:
        markup = ADMIN_REPLY_MARKUP if is_admin else MAIN_REPLY_MARKUP
        bot_reply = f"Вітаю, {bot_user.first_name}!"
        await update.message.reply_text(bot_reply, reply_markup=markup)
    else:
        btn = KeyboardButton("Надати номер телефону", request_contact=True)
        bot_reply = "Я вас не знаю. Надайте номер:"
        await update.message.reply_text(bot_reply, reply_markup=ReplyKeyboardMarkup([[btn]], resize_keyboard=True))

    if bot_user:
        await log_message_to_db(bot_user, '/start', bot_reply, message_type='command')

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    bot_user = await get_or_create_bot_user(user)
    bot_reply = await link_bot_user_by_phone(bot_user, update.message.contact.phone_number)

    is_linked, is_admin, _ = await check_if_user_is_linked(user.id)
    markup = ADMIN_REPLY_MARKUP if is_admin else (MAIN_REPLY_MARKUP if is_linked else None)

    await update.message.reply_text(bot_reply, reply_markup=markup)

    if bot_user:
        await log_message_to_db(bot_user, f"[контакт] {update.message.contact.phone_number}", bot_reply, message_type='contact')

async def my_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    bot_user = await get_or_create_bot_user(user)
    res = await get_my_cars_with_keyboard(bot_user)
    await update.message.reply_text(res["reply_text"], reply_markup=res["keyboard"])

    if bot_user:
        await log_message_to_db(bot_user, update.message.text, res["reply_text"])

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user
    bot_user = await get_or_create_bot_user(user)

    if context.user_data.get('awaiting_mileage_truck_id') and text.strip().isdigit():
        truck_id = context.user_data.pop('awaiting_mileage_truck_id')
        mileage = int(text.strip())
        truck, bot_reply = await save_mileage_report(bot_user, truck_id, mileage)
        await update.message.reply_text(bot_reply, parse_mode='Markdown')
    elif context.user_data.get('awaiting_truck'):
        bot_reply = await find_truck_by_plate(text)
        await update.message.reply_text(bot_reply)
        context.user_data['awaiting_truck'] = False
    elif context.user_data.get('awaiting_client'):
        bot_reply = await find_client_by_name(text)
        await update.message.reply_text(bot_reply)
        context.user_data['awaiting_client'] = False
    elif context.user_data.get('awaiting_order'):
        bot_reply = await get_order_status(text)
        await update.message.reply_text(bot_reply, parse_mode='Markdown')
        context.user_data['awaiting_order'] = False
    elif context.user_data.get('awaiting_photo_order'):
        orders = await get_orders_for_photo(text)
        if not orders:
            bot_reply = f"❌ Замовлення '{text}' не знайдено. Спробуйте ще раз."
            await update.message.reply_text(bot_reply)
        elif len(orders) == 1:
            order = orders[0]
            plate = order.truck.license_plate if order.truck else '—'
            context.user_data['photo_order_id'] = order.id
            context.user_data['awaiting_photo_order'] = False
            bot_reply = f"✅ Замовлення *{order.order_number}* ({plate})\n\nОберіть тип фото:"
            await update.message.reply_text(
                bot_reply,
                parse_mode='Markdown',
                reply_markup=get_photo_type_keyboard()
            )
        else:
            bot_reply = f"Знайдено {len(orders)} замовлень. Оберіть потрібне:"
            await update.message.reply_text(
                bot_reply,
                reply_markup=get_order_selection_keyboard(orders)
            )
    elif "Нагадування" in text:
        reminders = await get_client_reminders(bot_user)
        if not reminders:
            bot_reply = "✅ Активних нагадувань немає."
            await update.message.reply_text(bot_reply)
        else:
            lines = ["🔔 *Нагадування про обслуговування:*\n"]
            for r in reminders:
                status_icon = {"pending": "⏳", "notified": "📬", "overdue": "🚨"}.get(r['status'], "🔔")
                lines.append(f"{status_icon} *{r['title']}*")
                lines.append(f"   🚚 {r['plate']}")
                if r['km_left'] is not None:
                    if r['km_left'] > 0:
                        lines.append(f"   📏 Залишилось: ~{r['km_left']:,} км".replace(",", " "))
                    else:
                        lines.append(f"   ⚠️ Пробіг перевищено на {abs(r['km_left']):,} км!".replace(",", " "))
                if r['days_left'] is not None:
                    if r['days_left'] > 0:
                        lines.append(f"   📅 Залишилось: {r['days_left']} днів")
                    elif r['days_left'] == 0:
                        lines.append(f"   📅 Термін сьогодні!")
                    else:
                        lines.append(f"   📅 Прострочено на {abs(r['days_left'])} днів!")
                lines.append("")
            bot_reply = "\n".join(lines)
            await update.message.reply_text(bot_reply, parse_mode='Markdown')
    elif "Перевірити статус замовлення" in text:
        bot_reply = "Введіть номер замовлення:"
        context.user_data['awaiting_order'] = True
        await update.message.reply_text(bot_reply)
    else:
        bot_reply = "Оберіть дію з меню."
        await update.message.reply_text(bot_reply)

    if bot_user:
        await log_message_to_db(bot_user, text, bot_reply)

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user
    is_linked, is_admin, bot_user = await check_if_user_is_linked(user.id)

    if not is_admin:
        bot_reply = "Доступ заборонено."
        await update.message.reply_text(bot_reply)
        if bot_user:
            await log_message_to_db(bot_user, text, bot_reply)
        return

    bot_reply = ''
    if "Всі автомобілі" in text:
        bot_reply = await get_all_trucks()
        await update.message.reply_text(bot_reply)
    elif "Всі замовлення" in text:
        bot_reply = await get_all_orders()
        await update.message.reply_text(bot_reply)
    elif "Статистика" in text:
        bot_reply = await get_statistics()
        await update.message.reply_text(bot_reply)
    elif "Знайти авто" in text:
        bot_reply = "Введіть номер авто:"
        context.user_data['awaiting_truck'] = True
        await update.message.reply_text(bot_reply)
    elif "Знайти клієнта" in text:
        bot_reply = "Введіть ім'я:"
        context.user_data['awaiting_client'] = True
        await update.message.reply_text(bot_reply)
    elif "Фото замовлення" in text:
        bot_reply = "Введіть номер замовлення або останні цифри (наприклад: 0001):"
        context.user_data['awaiting_photo_order'] = True
        await update.message.reply_text(bot_reply)

    if bot_user:
        await log_message_to_db(bot_user, text, bot_reply)

PHOTO_TYPE_LABELS = {
    'car': 'Номерний знак',
    'odometer': 'Одометр',
    'dashboard': 'Панель приладів',
    'repair': 'Фото ремонту',
}


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if "history_" in query.data:
        truck_id = query.data.split("_")[1]
        await query.edit_message_text(await get_repair_history(truck_id))

    elif query.data.startswith("mileage_truck_"):
        truck_id = int(query.data.replace("mileage_truck_", ""))
        truck = await sync_to_async(
            lambda: Truck.objects.get(id=truck_id)
        )()
        context.user_data['awaiting_mileage_truck_id'] = truck_id
        await query.edit_message_text(
            f"🚚 *{truck.license_plate}* ({truck.specific_model_name})\n\n"
            "Введіть поточний пробіг в км (тільки число, наприклад: 185000):",
            parse_mode='Markdown'
        )

    elif query.data.startswith("photo_order_"):
        order_id = int(query.data.replace("photo_order_", ""))
        order = await sync_to_async(
            lambda: ServiceOrder.objects.select_related('truck').get(id=order_id)
        )()
        plate = order.truck.license_plate if order.truck else '—'
        context.user_data['photo_order_id'] = order_id
        context.user_data['awaiting_photo_order'] = False
        await query.edit_message_text(
            f"✅ Замовлення *{order.order_number}* ({plate})\n\nОберіть тип фото:",
            parse_mode='Markdown',
            reply_markup=get_photo_type_keyboard()
        )

    elif query.data.startswith("photo_type_"):
        photo_type = query.data.replace("photo_type_", "")
        order_id = context.user_data.get('photo_order_id')
        if not order_id:
            await query.edit_message_text("❌ Сесія завершена. Почніть знову через «📷 Фото замовлення».")
            return
        context.user_data['pending_photo_type'] = photo_type
        label = PHOTO_TYPE_LABELS.get(photo_type, photo_type)
        await query.edit_message_text(
            f"📸 Тип: *{label}*\n\nНадішліть фото:",
            parse_mode='Markdown'
        )

    elif query.data == "photo_cancel":
        context.user_data.pop('photo_order_id', None)
        context.user_data.pop('pending_photo_type', None)
        context.user_data.pop('awaiting_photo_order', None)
        await query.edit_message_text("❌ Завантаження фото скасовано.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє фото від адміна і прив'язує до замовлення."""
    user = update.message.from_user
    is_linked, is_admin, bot_user = await check_if_user_is_linked(user.id)

    if not is_admin:
        await update.message.reply_text("❌ Завантаження фото доступне тільки адміністраторам.")
        return

    photo_type = context.user_data.get('pending_photo_type')
    order_id = context.user_data.get('photo_order_id')

    if not photo_type or not order_id:
        await update.message.reply_text(
            "ℹ️ Оберіть замовлення і тип фото через кнопку «📷 Фото замовлення»."
        )
        return

    # Беремо найвищу якість (остання в списку = найбільша)
    photo = update.message.photo[-1]
    file_obj = await context.bot.get_file(photo.file_id)
    photo_bytes = await file_obj.download_as_bytearray()

    label = PHOTO_TYPE_LABELS.get(photo_type, photo_type)
    filename = f"{photo_type}_{order_id}_{photo.file_id[-8:]}.jpg"

    try:
        if photo_type == 'repair':
            await save_repair_photo(order_id, bytes(photo_bytes), filename)
        else:
            await save_order_photo(order_id, photo_type, bytes(photo_bytes), filename)

        # Очищуємо стан — тип фото скидаємо, замовлення лишаємо для наступних фото
        context.user_data.pop('pending_photo_type', None)

        await update.message.reply_text(
            f"✅ *{label}* збережено!\n\n"
            "Оберіть наступний тип фото або натисніть іншу кнопку меню.",
            parse_mode='Markdown',
            reply_markup=get_photo_type_keyboard()
        )
    except Exception as e:
        logger.error(f"Помилка збереження фото: {e}")
        await update.message.reply_text("❌ Помилка при збереженні фото. Спробуйте ще раз.")

    if bot_user:
        await log_message_to_db(bot_user, f"[photo] {label} → order_id={order_id}", "photo saved", message_type='photo')


# --- COMMAND ---
class Command(BaseCommand):
    help = 'Run Bot'
    def handle(self, *args, **options):
        if not BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN не встановлений у змінних середовища")
        app = Application.builder().token(BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
        app.add_handler(MessageHandler(filters.Regex("^Мої автомобілі"), my_cars))
        
        # Адмінські кнопки
        admin_regex = "^(Всі автомобілі|Всі замовлення|Статистика|Знайти авто|Знайти клієнта|📷 Фото замовлення)"
        app.add_handler(MessageHandler(filters.Regex(admin_regex), admin_buttons))
        
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        app.add_handler(CallbackQueryHandler(callback_handler))
        
        print("Бот працює...")
        app.run_polling()