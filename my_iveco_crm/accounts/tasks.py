import asyncio
import logging
import os

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def notify_admins_contact_form(name, phone, message):
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return

    try:
        from bot.models import BotUser
        from telegram import Bot

        admins = list(BotUser.objects.filter(role='admin', is_active=True))
        if not admins:
            logger.warning('ContactForm: немає admin BotUser для надсилання')
            return

        text = f'📩 *Нова заявка з сайту*\n\n👤 Ім\'я: {name}\n📞 Телефон: {phone}'
        if message:
            text += f'\n💬 Повідомлення: {message}'

        bot = Bot(token=bot_token)
        for admin in admins:
            try:
                asyncio.run(bot.send_message(
                    chat_id=admin.telegram_id,
                    text=text,
                    parse_mode='Markdown',
                ))
            except Exception as e:
                logger.error(f'ContactForm: помилка надсилання до {admin.telegram_id}: {e}')

    except Exception as e:
        logger.error(f'ContactForm: notify_admins_contact_form помилка: {e}')
