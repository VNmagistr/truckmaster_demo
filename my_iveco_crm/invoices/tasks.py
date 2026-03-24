import asyncio
import logging
import os

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def send_ttn_telegram(telegram_chat_id, text, invoice_number):
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return
    try:
        from telegram import Bot
        bot = Bot(token=bot_token)
        asyncio.run(bot.send_message(chat_id=telegram_chat_id, text=text))
    except Exception as e:
        logger.error(f'send_ttn_telegram error (invoice {invoice_number}): {e}')
