# bot/handlers/manager.py

"""
Обробники для менеджерів
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from ..utils import log_message, require_role
from ..services import TruckService

logger = logging.getLogger(__name__)


@log_message
@require_role('manager', 'admin')
async def search_truck_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /search - пошук автомобіля по номеру
    """
    if not context.args:
        await update.message.reply_text(
            "🔍 *Пошук автомобіля*\n\n"
            "Використання:\n"
            "`/search НОМЕР`\n\n"
            "Приклад:\n"
            "`/search AA1234BB`\n"
            "`/search 1234` (пошук по останніх цифрах)",
            parse_mode='Markdown'
        )
        return
    
    query = ' '.join(context.args)
    
    trucks = await TruckService.search_truck_by_plate(query)
    
    if not trucks:
        await update.message.reply_text(
            f"❌ Автомобілі з номером '{query}' не знайдено.\n"
            "Спробуйте інший запит."
        )
        return
    
    if len(trucks) == 1:
        # Один результат - показуємо повну інформацію
        truck = trucks[0]
        info = await TruckService.get_truck_info(truck)
        await update.message.reply_text(info, parse_mode='Markdown')
    else:
        # Кілька результатів - показуємо список
        text = f"🔍 *Знайдено автомобілів: {len(trucks)}*\n\n"
        
        for truck in trucks[:10]:  # Обмежуємо 10 результатами
            text += f"🚚 {truck.license_plate} - {truck.specific_model_name}\n"
            if truck.client:
                text += f"   👤 {truck.client.name}\n"
                if truck.client.phone:
                    text += f"   📞 {truck.client.phone}\n"
            text += "\n"
        
        if len(trucks) > 10:
            text += f"_(та ще {len(trucks) - 10} результатів)_\n"
        
        text += "\nВикористайте точний номер для детальної інформації."
        
        await update.message.reply_text(text, parse_mode='Markdown')


@log_message
@require_role('manager', 'admin')
async def clients_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /clients - список клієнтів (для менеджерів)
    """
    await update.message.reply_text(
        "👥 *Клієнти*\n\n"
        "Для пошуку клієнта використайте:\n"
        "• `/search НОМЕР_АВТО` - знайти по автомобілю\n"
        "• Або зверніться до CRM системи для повного списку",
        parse_mode='Markdown'
    )


@log_message
@require_role('manager', 'admin')
async def notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /notify - відправити сповіщення клієнту
    """
    await update.message.reply_text(
        "📬 *Відправити сповіщення*\n\n"
        "Функція в розробці.\n\n"
        "Планується:\n"
        "• Сповіщення про готовність автомобіля\n"
        "• Сповіщення про прибуття запчастин\n"
        "• Масові розсилки\n"
        "• Персональні повідомлення",
        parse_mode='Markdown'
    )


# ========== ЕКСПОРТ ОБРОБНИКІВ ==========

manager_handlers = [
    CommandHandler('search', search_truck_command),
    CommandHandler('clients', clients_command),
    CommandHandler('notify', notify_command),
]