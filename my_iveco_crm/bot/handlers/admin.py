"""Хендлери адмін-кнопок."""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.queries import (
    check_if_user_is_linked, log_message_to_db,
    get_all_trucks, get_all_orders, get_statistics,
)

logger = logging.getLogger(__name__)


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
