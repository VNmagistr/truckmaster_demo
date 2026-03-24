import logging
import os

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Appointment

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_telegram_chat_id(appt: Appointment):
    if appt.client and appt.client.telegram_chat_id:
        return appt.client.telegram_chat_id
    from clients.models import Client
    client = Client.objects.filter(phone=appt.client_phone).first()
    if client and client.telegram_chat_id:
        return client.telegram_chat_id
    return None


def _get_whatsapp_phone(appt: Appointment):
    if appt.client_phone:
        return appt.client_phone
    if appt.client and appt.client.phone:
        return appt.client.phone
    return None

def _send_whatsapp(phone, text):
    try:
        from my_iveco_crm.whatsapp import send_whatsapp_text
        send_whatsapp_text(phone, text)
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

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
    """Send confirmation via Telegram + WhatsApp when status → confirmed."""
    previous = getattr(instance, '_previous_status', None)
    if instance.status != 'confirmed' or previous == 'confirmed' or instance.confirmation_sent:
        return

    dt_str = instance.scheduled_dt.strftime('%d.%m.%Y о %H:%M')
    base = (
        f"📅 Дата: {dt_str}\n"
        f"🚗 Авто: {instance.license_plate}\n"
        f"🔧 Послуга: {instance.get_service_type_display()}\n\n"
        f"Чекаємо вас у сервісному центрі Італ Трак!\n"
        f"📞 +380 XX XXX XXXX"
    )

    # Telegram (Markdown)
    chat_id = _get_telegram_chat_id(instance)
    if chat_id:
        from appointments.tasks import send_confirmation_telegram
        send_confirmation_telegram.delay(chat_id, f"\u2705 *\u0417\u0430\u043f\u0438\u0441 \u043f\u0456\u0434\u0442\u0432\u0435\u0440\u0434\u0436\u0435\u043d\u043e*\u005c\u006e\u005c\u006e{base}")

    # WhatsApp (plain text)
    phone = _get_whatsapp_phone(instance)
    if phone:
        _send_whatsapp(phone, f"✅ Запис підтверджено!\n\n{base}")

    Appointment.objects.filter(pk=instance.pk).update(confirmation_sent=True)
