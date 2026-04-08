"""Клавіатури та константи Telegram-бота."""
from django.utils import timezone
from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

# ── Reply-клавіатури ─────────────────────────────────────────────────────────

MAIN_KEYBOARD = [
    [KeyboardButton("Мої автомобілі 🚚")],
    [KeyboardButton("Перевірити статус замовлення 🧾")],
    [KeyboardButton("📦 Мої відправки")],
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

# ── Inline-клавіатури ────────────────────────────────────────────────────────

PHOTO_TYPE_LABELS = {
    'car': 'Номерний знак',
    'odometer': 'Одометр',
    'dashboard': 'Панель приладів',
    'repair': 'Фото ремонту',
}


def get_photo_type_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📷 Номерний знак",   callback_data="photo_type_car"),
            InlineKeyboardButton("🔢 Одометр",          callback_data="photo_type_odometer"),
        ],
        [
            InlineKeyboardButton("🎛 Панель приладів",  callback_data="photo_type_dashboard"),
            InlineKeyboardButton("🔧 Фото ремонту",     callback_data="photo_type_repair"),
        ],
        [InlineKeyboardButton("❌ Скасувати", callback_data="photo_cancel")],
    ])


def get_order_selection_keyboard(orders):
    """Inline-клавіатура з переліком знайдених замовлень для вибору фото."""
    keyboard = []
    for order in orders:
        plate = order.truck.license_plate if order.truck else '—'
        date  = timezone.localtime(order.created_at).strftime('%d.%m.%y')
        label = f"№{order.order_number}  {plate}  {date}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"photo_order_{order.id}")])
    keyboard.append([InlineKeyboardButton("❌ Скасувати", callback_data="photo_cancel")])
    return InlineKeyboardMarkup(keyboard)


def get_truck_menu_keyboard(truck_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Історія ремонтів",   callback_data=f"truck_history_{truck_id}")],
        [InlineKeyboardButton("🔧 Регламентні роботи", callback_data=f"maintenance_truck_{truck_id}")],
    ])


def get_maintenance_action_keyboard(truck_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Коли виконувались роботи", callback_data=f"maint_history_{truck_id}")],
        [InlineKeyboardButton("📏 Залишок до ТО",             callback_data=f"maint_remaining_{truck_id}")],
    ])


def get_declarations_keyboard(invoices):
    """Inline-клавіатура з переліком декларацій НП."""
    keyboard = []
    for inv in invoices:
        total = float(inv.total or 0)
        label = (
            f"{inv.date.strftime('%d.%m.%Y')} · {total:,.0f} ₴ · "
            f"{inv.nova_poshta_declaration}"
        ).replace(',', ' ')
        keyboard.append([InlineKeyboardButton(label, callback_data=f"np_track_{inv.nova_poshta_declaration}")])
    keyboard.append([InlineKeyboardButton("❌ Закрити", callback_data="np_close")])
    return InlineKeyboardMarkup(keyboard)
