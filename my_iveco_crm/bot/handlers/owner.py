from django.utils import timezone
# bot/handlers/owner.py

"""
Обробники для власників автомобілів
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from ..utils import log_message, require_role
from ..services import UserService, OrderService, TruckService

logger = logging.getLogger(__name__)


@log_message
@require_role('owner', 'manager', 'admin')
async def check_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /order - перевірити статус замовлення
    """
    # Якщо є аргумент - це номер замовлення
    if context.args:
        order_number = context.args[0]
        await show_order_info(update, order_number)
    else:
        await update.message.reply_text(
            "📝 *Перевірка замовлення*\n\n"
            "Надішліть номер замовлення або використайте:\n"
            "`/order НОМЕР`\n\n"
            "Приклад: `/order 12345`",
            parse_mode='Markdown'
        )


async def show_order_info(update: Update, order_number: str):
    """Показує інформацію про замовлення"""
    order = await OrderService.get_order_by_number(order_number)
    
    if not order:
        await update.message.reply_text(
            f"❌ Замовлення #{order_number} не знайдено.\n"
            "Перевірте номер та спробуйте ще раз."
        )
        return
    
    info = await OrderService.get_order_info(order)
    await update.message.reply_text(info, parse_mode='Markdown')


@log_message
@require_role('owner', 'manager', 'admin')
async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /history - історія всіх ремонтів
    """
    user = update.effective_user
    bot_user = await UserService.get_user_by_telegram_id(user.id)
    
    # Отримуємо всі автомобілі користувача
    trucks = await TruckService.get_user_trucks(bot_user)
    
    if not trucks:
        await update.message.reply_text(
            "🚫 У вас немає закріплених автомобілів."
        )
        return
    
    text = "📜 *Історія ремонтів*\n\n"
    
    for truck in trucks:
        orders = await OrderService.get_truck_orders(truck, limit=3)
        
        text += f"🚚 *{truck.license_plate}* ({truck.specific_model_name})\n"
        
        if orders:
            for order in orders:
                text += f"  • №{order.order_number} - {timezone.localtime(order.created_at).strftime('%d.%m.%Y')} - {order.get_status_display()}\n"
        else:
            text += f"  _(історія відсутня)_\n"
        
        text += "\n"
    
    text += "Для детальної інформації використайте /mycars"
    
    await update.message.reply_text(text, parse_mode='Markdown')


@log_message
@require_role('owner', 'manager', 'admin')
async def active_orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /active - активні замовлення
    """
    user = update.effective_user
    bot_user = await UserService.get_user_by_telegram_id(user.id)
    
    orders = await OrderService.get_active_orders(bot_user)
    
    if not orders:
        await update.message.reply_text(
            "📝 У вас немає активних замовлень.\n\n"
            "Всі ваші автомобілі зараз не обслуговуються."
        )
        return
    
    text = f"📝 *Активні замовлення ({len(orders)}):*\n\n"
    
    for order in orders:
        text += f"🔸 №{order.order_number}\n"
        text += f"   🚚 {order.truck.license_plate}\n"
        text += f"   📊 {order.get_status_display()}\n"
        text += f"   📅 {timezone.localtime(order.created_at).strftime('%d.%m.%Y')}\n"
        if order.total_cost:
            text += f"   💰 {order.total_cost} грн\n"
        text += "\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')


@log_message
@require_role('owner', 'manager', 'admin')
async def contacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /contacts - контакти сервісного центру
    """
    text = (
        "📞 *Контакти сервісного центру*\n\n"
        "📍 Адреса:\n"
        "[вказати адресу]\n\n"
        "☎️ Телефон:\n"
        "[вказати телефон]\n\n"
        "📧 Email:\n"
        "[вказати email]\n\n"
        "🕐 Графік роботи:\n"
        "Пн-Пт: 9:00-18:00\n"
        "Сб: 10:00-15:00\n"
        "Нд: вихідний\n\n"
        "💬 Для запитань пишіть сюди або телефонуйте."
    )
    
    await update.message.reply_text(text, parse_mode='Markdown')


# ========== ЕКСПОРТ ОБРОБНИКІВ ==========

owner_handlers = [
    CommandHandler('order', check_order_command),
    CommandHandler('history', history_command),
    CommandHandler('active', active_orders_command),
    CommandHandler('contacts', contacts_command),
]