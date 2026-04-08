"""
Thin wrapper around the Telegram Bot API.

send_message()       — синхронна версія для Celery-воркерів та Django views.
                       З gevent-пулом requests I/O автоматично yields.
async_send_message() — async-обгортка для використання в asyncio-контексті
                       (наприклад, хендлери python-telegram-bot).
                       Запускає синхронний HTTP у thread-pool, не блокуючи event loop.
"""
import asyncio
import logging
import os

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 10  # seconds


def send_message(chat_id, text, parse_mode='Markdown', reply_markup=None, token=None):
    """
    Send a Telegram message. reply_markup must be a plain dict
    matching the Telegram Bot API schema (e.g. {'inline_keyboard': [...]}).
    """
    bot_token = token or os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.warning('tg.send_message: TELEGRAM_BOT_TOKEN not set')
        return

    payload = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        payload['parse_mode'] = parse_mode
    if reply_markup is not None:
        payload['reply_markup'] = reply_markup

    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    try:
        resp = requests.post(url, json=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f'tg.send_message error (chat_id={chat_id}): {e}')


async def async_send_message(chat_id, text, parse_mode='Markdown', reply_markup=None, token=None):
    """
    Async-safe версія send_message для використання в asyncio-контексті.
    Виконує блокуючий HTTP-запит у thread-pool executor, не блокуючи event loop.
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: send_message(chat_id, text, parse_mode, reply_markup, token),
    )
