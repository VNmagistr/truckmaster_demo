import logging

from celery import shared_task

from core.telegram import send_message as tg_send

logger = logging.getLogger(__name__)


@shared_task
def notify_admins_contact_form(name, phone, message):
    try:
        from bot.models import BotUser
        admins = list(BotUser.objects.filter(role='admin', is_active=True))
        if not admins:
            logger.warning('ContactForm: немає admin BotUser для надсилання')
            return

        text = f'📩 *Нова заявка з сайту*\n\n👤 Ім\'я: {name}\n📞 Телефон: {phone}'
        if message:
            text += f'\n💬 Повідомлення: {message}'

        for admin in admins:
            tg_send(admin.telegram_id, text)
    except Exception as e:
        logger.error(f'notify_admins_contact_form error: {e}')
