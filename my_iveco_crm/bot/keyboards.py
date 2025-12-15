# bot/keyboards.py

"""
Клавіатури для Telegram бота
"""

from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


# ========== ГОЛОВНІ МЕНЮ ==========

def get_guest_keyboard():
    """Клавіатура для гостей"""
    keyboard = [
        [KeyboardButton("📞 Надати контакт", request_contact=True)],
        [KeyboardButton("ℹ️ Інформація"), KeyboardButton("❓ Допомога")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_driver_keyboard():
    """Клавіатура для водіїв"""
    keyboard = [
        [KeyboardButton("🚚 Мої автомобілі")],
        [KeyboardButton("🔔 Нагадування"), KeyboardButton("📋 Графік ТО")],
        [KeyboardButton("ℹ️ Інформація"), KeyboardButton("⚙️ Налаштування")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_owner_keyboard():
    """Клавіатура для власників"""
    keyboard = [
        [KeyboardButton("🚚 Мої автомобілі")],
        [KeyboardButton("📝 Перевірити замовлення"), KeyboardButton("📜 Історія")],
        [KeyboardButton("🔔 Нагадування"), KeyboardButton("📞 Контакти")],
        [KeyboardButton("⚙️ Налаштування")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_manager_keyboard():
    """Клавіатура для менеджерів"""
    keyboard = [
        [KeyboardButton("🚚 Пошук автомобіля"), KeyboardButton("👥 Клієнти")],
        [KeyboardButton("📝 Створити замовлення"), KeyboardButton("📊 Звіти")],
        [KeyboardButton("📬 Відправити сповіщення")],
        [KeyboardButton("⚙️ Налаштування")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_admin_keyboard():
    """Клавіатура для адміністраторів"""
    keyboard = [
        [KeyboardButton("🔍 Знайти автомобіль"), KeyboardButton("👥 Користувачі")],
        [KeyboardButton("📝 Замовлення"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("📋 Логи бота"), KeyboardButton("📬 Сповіщення")],
        [KeyboardButton("⚙️ Налаштування"), KeyboardButton("❓ Допомога")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_main_keyboard_for_role(role):
    """Повертає відповідну клавіатуру залежно від ролі"""
    keyboards = {
        'guest': get_guest_keyboard(),
        'driver': get_driver_keyboard(),
        'owner': get_owner_keyboard(),
        'manager': get_manager_keyboard(),
        'admin': get_admin_keyboard(),
    }
    return keyboards.get(role, get_guest_keyboard())


# ========== INLINE КЛАВІАТУРИ ==========

def get_truck_selection_keyboard(trucks):
    """Інлайн клавіатура для вибору автомобіля"""
    keyboard = []
    for truck in trucks:
        button_text = f"🚚 {truck.license_plate} ({truck.specific_model_name})"
        keyboard.append([InlineKeyboardButton(
            button_text, 
            callback_data=f"truck_{truck.id}"
        )])
    keyboard.append([InlineKeyboardButton("❌ Скасувати", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)


def get_truck_actions_keyboard(truck_id):
    """Клавіатура з діями для конкретного автомобіля"""
    keyboard = [
        [InlineKeyboardButton("📜 Історія ремонтів", callback_data=f"history_{truck_id}")],
        [InlineKeyboardButton("📋 Графік ТО", callback_data=f"schedule_{truck_id}")],
        [InlineKeyboardButton("🔔 Налаштувати нагадування", callback_data=f"reminders_{truck_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_trucks")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_reminder_types_keyboard():
    """Клавіатура для вибору типу нагадування"""
    keyboard = [
        [InlineKeyboardButton("🛢️ Заміна оливи", callback_data="reminder_oil_change")],
        [InlineKeyboardButton("🔧 Планове ТО", callback_data="reminder_maintenance")],
        [InlineKeyboardButton("📦 Прибуття запчастини", callback_data="reminder_part_arrival")],
        [InlineKeyboardButton("✅ Завершення ремонту", callback_data="reminder_service_complete")],
        [InlineKeyboardButton("🚗 Техогляд", callback_data="reminder_inspection_due")],
        [InlineKeyboardButton("📄 Страховка", callback_data="reminder_insurance_due")],
        [InlineKeyboardButton("❌ Скасувати", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_reminder_settings_keyboard(setting_id):
    """Клавіатура для налаштування конкретного нагадування"""
    keyboard = [
        [InlineKeyboardButton("✏️ Змінити час", callback_data=f"edit_time_{setting_id}")],
        [InlineKeyboardButton("📅 Змінити дні", callback_data=f"edit_days_{setting_id}")],
        [InlineKeyboardButton("🚫 Вимкнути", callback_data=f"disable_{setting_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_reminders")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(action, item_id):
    """Клавіатура підтвердження дії"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Так", callback_data=f"confirm_{action}_{item_id}"),
            InlineKeyboardButton("❌ Ні", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_logs_keyboard():
    """Клавіатура для адміна - перегляд логів"""
    keyboard = [
        [InlineKeyboardButton("📋 Останні 15 повідомлень", callback_data="logs_recent_15")],
        [InlineKeyboardButton("📊 Статистика за сьогодні", callback_data="logs_today")],
        [InlineKeyboardButton("📈 Статистика за тиждень", callback_data="logs_week")],
        [InlineKeyboardButton("❌ Закрити", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_button():
    """Проста кнопка "Назад" """
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
    return InlineKeyboardMarkup(keyboard)


def get_cancel_button():
    """Проста кнопка "Скасувати" """
    keyboard = [[InlineKeyboardButton("❌ Скасувати", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)


# ========== ДОПОМІЖНІ ФУНКЦІЇ ==========

def remove_keyboard():
    """Видаляє клавіатуру"""
    from telegram import ReplyKeyboardRemove
    return ReplyKeyboardRemove()