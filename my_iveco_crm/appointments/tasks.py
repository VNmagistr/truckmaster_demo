import asyncio
import logging
import os
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from telegram import Bot
from telegram.error import TelegramError

from .models import Appointment
from .signals import _get_telegram_chat_id

logger = logging.getLogger(__name__)
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')


@shared_task
def send_appointment_reminders():
    """
    Runs every hour. Finds confirmed appointments starting in 22-26h
    and sends a Telegram reminder if not yet sent.
    """
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return 0

    now = timezone.now()
    window_start = now + timedelta(hours=22)
    window_end = now + timedelta(hours=26)

    appointments = Appointment.objects.filter(
        status='confirmed',
        reminder_sent=False,
        scheduled_dt__gte=window_start,
        scheduled_dt__lte=window_end,
    )

    bot = Bot(token=BOT_TOKEN)
    sent_count = 0

    for appt in appointments:
        chat_id = _get_telegram_chat_id(appt)
        if not chat_id:
            continue
        try:
            dt_str = appt.scheduled_dt.strftime('%d.%m.%Y о %H:%M')
            text = (
                f"🔔 *Нагадування про запис на СТО*\n\n"
                f"Завтра о *{appt.scheduled_dt.strftime('%H:%M')}* ваш запис у *Італ Трак*.\n\n"
                f"📅 Дата: {dt_str}\n"
                f"🚗 Авто: {appt.license_plate}\n"
                f"🔧 Послуга: {appt.get_service_type_display()}\n\n"
                f"Якщо плани змінились — зателефонуйте нам заздалегідь.\n"
                f"📞 +380 XX XXX XXXX"
            )
            asyncio.run(bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown'))
            Appointment.objects.filter(pk=appt.pk).update(reminder_sent=True)
            sent_count += 1
            logger.info(f"Reminder sent for appointment {appt.pk}")
        except TelegramError as e:
            logger.error(f"Telegram error for appointment {appt.pk}: {e}")
        except Exception as e:
            logger.error(f"Error sending reminder for appointment {appt.pk}: {e}")

    logger.info(f"Sent {sent_count} appointment reminders")
    return sent_count
