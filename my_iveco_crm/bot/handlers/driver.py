from django.utils import timezone
# bot/handlers/driver.py

"""
Обробники для водіїв
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from ..models import BotUser
from ..utils import log_message, require_role
from ..services import UserService, TruckService, ReminderService
from ..keyboards import get_truck_selection_keyboard, get_truck_actions_keyboard

logger = logging.getLogger(__name__)


@log_message
@require_role('driver', 'owner', 'manager', 'admin')
async def my_cars_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /mycars - показати автомобілі водія
    """
    user = update.effective_user
    bot_user = await UserService.get_user_by_telegram_id(user.id)
    
    trucks = await TruckService.get_user_trucks(bot_user)
    
    if not trucks:
        await update.message.reply_text(
            "🚫 За вами не закріплено жодного автомобіля.\n"
            "Зверніться до менеджера для призначення."
        )
        return
    
    # Формуємо список автомобілів з кнопками
    text = f"🚚 *Ваші автомобілі ({len(trucks)}):*\n\n"
    
    keyboard = get_truck_selection_keyboard(trucks)
    
    await update.message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


@log_message
async def truck_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробник вибору автомобіля (callback від inline кнопок)
    """
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data.startswith('truck_'):
        # Вибрано автомобіль
        truck_id = int(callback_data.split('_')[1])
        truck = await TruckService.get_truck_by_id(truck_id)
        
        if not truck:
            await query.edit_message_text("❌ Автомобіль не знайдено")
            return
        
        # Показуємо інформацію про автомобіль
        info = await TruckService.get_truck_info(truck)
        keyboard = get_truck_actions_keyboard(truck_id)
        
        await query.edit_message_text(
            info,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    elif callback_data.startswith('history_'):
        # Показати історію ремонтів
        truck_id = int(callback_data.split('_')[1])
        await show_truck_history(query, truck_id)
    
    elif callback_data.startswith('schedule_'):
        # Показати графік ТО
        truck_id = int(callback_data.split('_')[1])
        await show_maintenance_schedule(query, truck_id)
    
    elif callback_data.startswith('reminders_'):
        # Налаштування нагадувань
        truck_id = int(callback_data.split('_')[1])
        await show_reminders_menu(query, truck_id)
    
    elif callback_data == 'back_to_trucks':
        # Повернутись до списку автомобілів
        user = query.from_user
        bot_user = await UserService.get_user_by_telegram_id(user.id)
        trucks = await TruckService.get_user_trucks(bot_user)
        
        text = f"🚚 *Ваші автомобілі ({len(trucks)}):*\n\n"
        keyboard = get_truck_selection_keyboard(trucks)
        
        await query.edit_message_text(
            text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    elif callback_data == 'cancel':
        await query.edit_message_text("✅ Скасовано")


async def show_truck_history(query, truck_id: int):
    """Показує історію ремонтів автомобіля"""
    from ..services import OrderService
    
    truck = await TruckService.get_truck_by_id(truck_id)
    if not truck:
        await query.edit_message_text("❌ Автомобіль не знайдено")
        return
    
    orders = await OrderService.get_truck_orders(truck, limit=5)
    
    if not orders:
        text = f"📜 *Історія ремонтів*\n\n"
        text += f"🚚 {truck.license_plate} ({truck.specific_model_name})\n\n"
        text += "Історія ремонтів відсутня."
    else:
        text = f"📜 *Історія ремонтів*\n\n"
        text += f"🚚 {truck.license_plate} ({truck.specific_model_name})\n\n"
        
        for order in orders:
            text += f"📝 №{order.order_number}\n"
            text += f"📅 {timezone.localtime(order.created_at).strftime('%d.%m.%Y')}\n"
            text += f"📊 {order.get_status_display()}\n"
            if order.total_cost:
                text += f"💰 {order.total_cost} грн\n"
            text += "\n"
        
        if len(orders) == 5:
            text += "_(Показано останні 5 записів)_"
    
    # Кнопка назад
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"truck_{truck_id}")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def show_maintenance_schedule(query, truck_id: int):
    """Показує графік планового ТО"""
    truck = await TruckService.get_truck_by_id(truck_id)
    if not truck:
        await query.edit_message_text("❌ Автомобіль не знайдено")
        return
    
    text = f"📋 *Графік ТО*\n\n"
    text += f"🚚 {truck.license_plate} ({truck.specific_model_name})\n\n"
    
    # TODO: Отримати реальний графік з maintenance додатку
    text += "🔧 Наступне ТО:\n"
    text += "• Заміна оливи: через 5000 км\n"
    text += "• Заміна фільтрів: через 8000 км\n"
    text += "• Планове ТО-2: через 12000 км\n\n"
    text += "Для деталей зверніться до менеджера."
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"truck_{truck_id}")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def show_reminders_menu(query, truck_id: int):
    """Показує меню налаштування нагадувань"""
    user = query.from_user
    bot_user = await UserService.get_user_by_telegram_id(user.id)
    truck = await TruckService.get_truck_by_id(truck_id)
    
    if not truck:
        await query.edit_message_text("❌ Автомобіль не знайдено")
        return
    
    reminders = await ReminderService.get_truck_reminders(bot_user, truck)
    
    text = f"🔔 *Налаштування нагадувань*\n\n"
    text += f"🚚 {truck.license_plate}\n\n"
    
    if reminders:
        text += "Активні нагадування:\n"
        for reminder in reminders:
            status = "✅" if reminder.is_enabled else "❌"
            text += f"{status} {reminder.get_reminder_type_display()}\n"
    else:
        text += "Нагадування не налаштовані.\n"
    
    text += "\nДля налаштування використайте команду /reminders"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"truck_{truck_id}")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


@log_message
@require_role('driver', 'owner', 'manager', 'admin')
async def reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /reminders - налаштування нагадувань
    """
    await update.message.reply_text(
        "🔔 *Налаштування нагадувань*\n\n"
        "Спочатку оберіть автомобіль за допомогою /mycars",
        parse_mode='Markdown'
    )


# ========== ЕКСПОРТ ОБРОБНИКІВ ==========

driver_handlers = [
    CommandHandler('mycars', my_cars_command),
    CommandHandler('reminders', reminders_command),
    CallbackQueryHandler(truck_callback_handler, pattern='^(truck_|history_|schedule_|reminders_|back_to_trucks|cancel)'),
]