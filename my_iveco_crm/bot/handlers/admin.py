# bot/handlers/admin.py

"""
Обробники для адміністраторів
Включає спеціальні функції: пошук автомобіля та перегляд логів
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from ..utils import log_message, require_role
from ..services import TruckService, LogService, UserService

logger = logging.getLogger(__name__)


@log_message
@require_role('admin')
async def admin_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /find - адмін-пошук автомобіля
    Підтримує пошук по повному номеру або останніх цифрах
    """
    if not context.args:
        await update.message.reply_text(
            "🔍 *АДМІН: Пошук автомобіля*\n\n"
            "Використання:\n"
            "`/find НОМЕР_АБО_ЦИФРИ`\n\n"
            "Приклади:\n"
            "`/find AA1234BB` - повний номер\n"
            "`/find 1234` - останні цифри\n"
            "`/find AA12` - частковий номер",
            parse_mode='Markdown'
        )
        return
    
    query = ' '.join(context.args)
    
    trucks = await TruckService.search_truck_by_plate(query)
    
    if not trucks:
        await update.message.reply_text(
            f"❌ *Результатів не знайдено*\n\n"
            f"Запит: `{query}`\n"
            "Спробуйте інший варіант пошуку.",
            parse_mode='Markdown'
        )
        return
    
    # Формуємо детальну відповідь з контактами
    if len(trucks) == 1:
        truck = trucks[0]
        text = "🔍 *ЗНАЙДЕНО:*\n\n"
        text += f"🚚 *Автомобіль:*\n"
        text += f"📋 Номер: `{truck.license_plate}`\n"
        text += f"🚗 Модель: {truck.specific_model_name}\n"
        text += f"🔢 VIN: `...{truck.last_seven_vin}`\n"
        
        if truck.euro_standard:
            text += f"♻️ Євростандарт: {truck.get_euro_standard_display()}\n"
        
        text += "\n"
        
        if truck.client:
            text += f"👤 *Власник:*\n"
            text += f"📛 {truck.client.name}\n"
            
            if truck.client.phone:
                text += f"📞 {truck.client.phone}\n"
            
            if truck.client.email:
                text += f"📧 {truck.client.email}\n"
            
            if truck.client.telegram_chat_id:
                text += f"💬 Telegram ID: `{truck.client.telegram_chat_id}`\n"
        else:
            text += "👤 *Власник:* не вказано\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    else:
        # Кілька результатів
        text = f"🔍 *Знайдено: {len(trucks)} автомобілів*\n\n"
        
        for i, truck in enumerate(trucks[:15], 1):  # Обмежуємо 15 результатами
            text += f"{i}. 🚚 `{truck.license_plate}` - {truck.specific_model_name}\n"
            
            if truck.client:
                text += f"   👤 {truck.client.name}\n"
                if truck.client.phone:
                    text += f"   📞 {truck.client.phone}\n"
            
            text += "\n"
        
        if len(trucks) > 15:
            text += f"_...та ще {len(trucks) - 15} результатів_\n\n"
        
        text += "💡 Використайте точний номер для детальної інформації"
        
        await update.message.reply_text(text, parse_mode='Markdown')


@log_message
@require_role('admin')
async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /logs - перегляд останніх логів бота
    Показує останні 15 повідомлень з телефонами та Telegram username
    """
    # Отримуємо кількість логів з аргументів (за замовчуванням 15)
    limit = 15
    if context.args:
        try:
            limit = int(context.args[0])
            limit = min(limit, 50)  # Максимум 50
        except ValueError:
            pass
    
    logs = await LogService.get_recent_logs(limit)
    
    if not logs:
        await update.message.reply_text(
            "📋 Логів не знайдено"
        )
        return
    
    text = f"📋 *ЛОГИ БОТА - Останні {len(logs)} повідомлень:*\n\n"
    
    for i, log in enumerate(logs, 1):
        # Час
        time_str = log.created_at.strftime('%d.%m %H:%M')
        
        # Напрямок
        direction = "➡️" if log.is_incoming else "⬅️"
        
        # Ім'я користувача
        name = log.bot_user.get_full_name()
        
        # Username
        username = f"@{log.bot_user.username}" if log.bot_user.username else "без username"
        
        # Телефон
        phone = log.bot_user.phone_number or "без телефону"
        
        # Повідомлення (скорочене)
        msg_preview = log.message_text[:40] + "..." if len(log.message_text) > 40 else log.message_text
        
        text += f"{i}. {time_str} {direction}\n"
        text += f"   👤 {name}\n"
        text += f"   📱 {username} | {phone}\n"
        text += f"   💬 `{msg_preview}`\n\n"
    
    text += f"_Використайте `/logs N` для перегляду N повідомлень (макс. 50)_"
    
    # Розбиваємо на частини якщо текст завеликий
    if len(text) > 4000:
        # Telegram має ліміт 4096 символів
        parts = []
        current = ""
        
        for line in text.split('\n'):
            if len(current) + len(line) < 4000:
                current += line + '\n'
            else:
                parts.append(current)
                current = line + '\n'
        
        if current:
            parts.append(current)
        
        for part in parts:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')


@log_message
@require_role('admin')
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /stats - статистика бота
    """
    stats = await LogService.get_bot_statistics()
    
    text = "📊 *СТАТИСТИКА БОТА*\n\n"
    
    text += f"👥 *Користувачі:*\n"
    text += f"   Всього: {stats['total_users']}\n"
    text += f"   Активні: {stats['active_users']}\n\n"
    
    text += f"📋 *По ролям:*\n"
    for role, count in stats['users_by_role'].items():
        role_names = {
            'guest': 'Гості',
            'driver': 'Водії',
            'owner': 'Власники',
            'manager': 'Менеджери',
            'admin': 'Адміністратори'
        }
        text += f"   {role_names.get(role, role)}: {count}\n"
    
    text += f"\n💬 *Повідомлення:*\n"
    text += f"   Всього: {stats['total_messages']}\n"
    text += f"   Сьогодні: {stats['today_messages']}\n"
    text += f"   Середній час обробки: {stats['avg_response_time_ms']:.0f} мс\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')


@log_message
@require_role('admin')
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /users - список користувачів бота
    """
    from ..models import BotUser
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def get_users():
        return list(BotUser.objects.all().order_by('-last_activity')[:20])
    
    users = await get_users()
    
    text = f"👥 *КОРИСТУВАЧІ БОТА (останні 20):*\n\n"
    
    for user in users:
        text += f"• {user.get_full_name()}\n"
        text += f"  Роль: {user.get_role_display()}\n"
        
        if user.phone_number:
            text += f"  📞 {user.phone_number}\n"
        
        if user.username:
            text += f"  📱 @{user.username}\n"
        
        text += f"  ID: `{user.telegram_id}`\n"
        text += f"  Активність: {user.last_activity.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    text += "_Для повного списку використайте Django Admin_"
    
    # Розбиваємо якщо занадто довго
    if len(text) > 4000:
        parts = []
        current = ""
        for line in text.split('\n'):
            if len(current) + len(line) < 4000:
                current += line + '\n'
            else:
                parts.append(current)
                current = line + '\n'
        if current:
            parts.append(current)
        
        for part in parts:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')


@log_message
@require_role('admin')
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /broadcast - масова розсилка (заглушка)
    """
    await update.message.reply_text(
        "📢 *Масова розсилка*\n\n"
        "⚠️ Функція в розробці\n\n"
        "Планується:\n"
        "• Розсилка всім користувачам\n"
        "• Розсилка по ролям\n"
        "• Розсилка по клієнтам\n"
        "• Планування розсилок",
        parse_mode='Markdown'
    )


# ========== ЕКСПОРТ ОБРОБНИКІВ ==========

admin_handlers = [
    CommandHandler('find', admin_search_command),
    CommandHandler('logs', logs_command),
    CommandHandler('stats', stats_command),
    CommandHandler('users', users_command),
    CommandHandler('broadcast', broadcast_command),
]