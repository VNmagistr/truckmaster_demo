import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from core.telegram import send_message as tg_send
from .models import Appointment
from .signals import _get_telegram_chat_id, _get_whatsapp_phone

logger = logging.getLogger(__name__)


@shared_task
def send_appointment_reminders():
    """
    Runs every hour. Finds confirmed appointments starting in 22-26h
    and sends a reminder via Telegram + WhatsApp if not yet sent.
    """
    now = timezone.now()
    window_start = now + timedelta(hours=22)
    window_end = now + timedelta(hours=26)

    appointments = Appointment.objects.filter(
        status='confirmed',
        reminder_sent=False,
        scheduled_dt__gte=window_start,
        scheduled_dt__lte=window_end,
    )

    sent_count = 0

    for appt in appointments:
        dt_str = timezone.localtime(appt.scheduled_dt).strftime('%d.%m.%Y о %H:%M')
        base = (
            f"📅 Дата: {dt_str}\n"
            f"🚗 Авто: {appt.license_plate}\n"
            f"🔧 Послуга: {appt.get_service_type_display()}\n\n"
            f"Якщо плани змінились — зателефонуйте нам заздалегідь.\n"
            f"📞 +380 XX XXX XXXX"
        )
        notified = False

        # --- Telegram ---
        chat_id = _get_telegram_chat_id(appt)
        if chat_id:
            try:
                tg_text = (
                    f"🔔 *Нагадування про запис на СТО*\n\n"
                    f"Завтра о *{timezone.localtime(appt.scheduled_dt).strftime('%H:%M')}* ваш запис у *Італ Трак*.\n\n"
                    f"{base}"
                )
                tg_send(chat_id, tg_text)
                notified = True
            except Exception as e:
                logger.error(f"Telegram reminder error for appt {appt.pk}: {e}")

        # --- WhatsApp ---
        phone = _get_whatsapp_phone(appt)
        if phone:
            try:
                from my_iveco_crm.whatsapp import send_whatsapp_text
                wa_text = (
                    f"🔔 Нагадування про запис на СТО\n\n"
                    f"Завтра о {timezone.localtime(appt.scheduled_dt).strftime('%H:%M')} ваш запис у Італ Трак.\n\n"
                    f"{base}"
                )
                send_whatsapp_text(phone, wa_text)
                notified = True
            except Exception as e:
                logger.error(f"WhatsApp reminder error for appt {appt.pk}: {e}")

        if notified:
            Appointment.objects.filter(pk=appt.pk).update(reminder_sent=True)
            sent_count += 1
            logger.info(f"Reminder sent for appointment {appt.pk}")

    logger.info(f"Sent {sent_count} appointment reminders")
    return sent_count


@shared_task
def send_confirmation_telegram(chat_id, text):
    tg_send(chat_id, text)
