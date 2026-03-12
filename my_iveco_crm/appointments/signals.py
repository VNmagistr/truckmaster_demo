import asyncio
import logging
import os

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Appointment

logger = logging.getLogger(__name__)


def _get_telegram_chat_id(appt: Appointment):
    """Try to find the client's telegram_chat_id."""
    if appt.client and appt.client.telegram_chat_id:
        return appt.client.telegram_chat_id
    # Search by phone number in clients
    from clients.models import Client
    client = Client.objects.filter(phone=appt.client_phone).first()
    if client and client.telegram_chat_id:
        return client.telegram_chat_id
    return None


def _send_telegram(chat_id, text):
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return
    try:
        from telegram import Bot
        bot = Bot(token=bot_token)
        asyncio.run(bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown'))
    except Exception as e:
        logger.error(f"Telegram send error: {e}")


@receiver(pre_save, sender=Appointment)
def capture_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._previous_status = Appointment.objects.only('status').get(pk=instance.pk).status
        except Appointment.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender=Appointment)
def send_confirmation_on_confirm(sender, instance, created, **kwargs):
    """Send Telegram confirmation when appointment status changes to 'confirmed'."""
    previous = getattr(instance, '_previous_status', None)
    if instance.status == 'confirmed' and previous != 'confirmed' and not instance.confirmation_sent:
        chat_id = _get_telegram_chat_id(instance)
        if not chat_id:
            return
        dt_str = instance.scheduled_dt.strftime('%d.%m.%Y о %H:%M')
        text = (
            f"✅ *Запис підтверджено*\n\n"
            f"📅 Дата: {dt_str}\n"
            f"🚗 Авто: {instance.license_plate}\n"
            f"🔧 Послуга: {instance.get_service_type_display()}\n\n"
            f"Чекаємо вас у сервісному центрі *Італ Трак*!\n"
            f"📍 Адреса: вул. Приклад, 1, Київ\n"
            f"📞 +380 XX XXX XXXX"
        )
        _send_telegram(chat_id, text)
        Appointment.objects.filter(pk=instance.pk).update(confirmation_sent=True)
