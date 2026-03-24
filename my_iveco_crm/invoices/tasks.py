import logging

from celery import shared_task

from core.telegram import send_message as tg_send

logger = logging.getLogger(__name__)


@shared_task
def send_ttn_telegram(telegram_chat_id, text, invoice_number):
    tg_send(telegram_chat_id, text, parse_mode=None)
