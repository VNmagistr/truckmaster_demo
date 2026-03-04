import logging
import os
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from telegram import Bot
from telegram.error import TelegramError

from .models import BotUser
from maintenance.models import ServiceReminder

logger = logging.getLogger(__name__)
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# За скільки км до цільового пробігу надсилати нагадування
MILEAGE_ALERT_THRESHOLD_KM = 2000
# За скільки днів до цільової дати надсилати нагадування
DATE_ALERT_THRESHOLD_DAYS = 14


def _build_reminder_message(reminder: ServiceReminder, current_mileage: int) -> str:
    truck = reminder.truck
    lines = [
        f"🔔 *Нагадування про технічне обслуговування*\n",
        f"🚚 {truck.license_plate} ({truck.specific_model_name})",
        f"🔧 {reminder.title}",
    ]

    if reminder.target_mileage and current_mileage:
        km_left = reminder.target_mileage - current_mileage
        lines.append(f"📊 Поточний пробіг: {current_mileage:,} км".replace(",", " "))
        lines.append(f"🎯 Виконати при: {reminder.target_mileage:,} км".replace(",", " "))
        if km_left > 0:
            lines.append(f"📏 Залишилось: ~{km_left:,} км".replace(",", " "))
        else:
            lines.append(f"⚠️ *Пробіг перевищено на {abs(km_left):,} км!*".replace(",", " "))

    if reminder.target_date:
        today = timezone.now().date()
        days_left = (reminder.target_date - today).days
        lines.append(f"📅 Дата: {reminder.target_date.strftime('%d.%m.%Y')}")
        if days_left < 0:
            lines.append(f"⚠️ *Прострочено на {abs(days_left)} днів!*")
        elif days_left == 0:
            lines.append("⚠️ *Термін сьогодні!*")
        else:
            lines.append(f"📏 Залишилось: {days_left} днів")

    lines.append("\nЗверніться до нашого сервісного центру для запису на обслуговування.")
    return "\n".join(lines)


def _is_due(reminder: ServiceReminder, current_mileage: int) -> bool:
    """Перевіряє чи настав час надіслати нагадування."""
    today = timezone.now().date()
    mileage_due = (
        reminder.target_mileage is not None
        and current_mileage >= reminder.target_mileage - MILEAGE_ALERT_THRESHOLD_KM
    )
    date_due = (
        reminder.target_date is not None
        and today >= reminder.target_date - timedelta(days=DATE_ALERT_THRESHOLD_DAYS)
    )

    if reminder.reminder_type == 'mileage':
        return mileage_due
    elif reminder.reminder_type == 'date':
        return date_due
    else:  # 'both'
        return mileage_due or date_due


@shared_task
def send_daily_reminders():
    """
    Щоденна задача: перевіряє ServiceReminder зі статусом 'pending'
    і надсилає Telegram-повідомлення власнику вантажівки якщо час підійшов.
    """
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не встановлений")
        return 0

    bot = Bot(token=BOT_TOKEN)

    pending = ServiceReminder.objects.filter(
        status='pending',
        truck__client__isnull=False,
    ).select_related('truck', 'truck__client', 'service_type')

    sent_count = 0

    for reminder in pending:
        try:
            truck = reminder.truck
            current_mileage = truck.get_latest_mileage()

            if not _is_due(reminder, current_mileage):
                continue

            # Знаходимо BotUser власника
            bot_user = BotUser.objects.filter(
                client=truck.client,
                is_active=True,
                is_blocked=False,
            ).first()

            if not bot_user:
                logger.debug(f"Власник {truck.client} не має акаунту в боті — пропускаємо")
                continue

            message = _build_reminder_message(reminder, current_mileage)

            import asyncio
            asyncio.run(bot.send_message(
                chat_id=bot_user.telegram_id,
                text=message,
                parse_mode='Markdown',
            ))

            reminder.status = 'notified'
            reminder.save(update_fields=['status'])
            sent_count += 1
            logger.info(f"Нагадування надіслано: {reminder} → {bot_user.telegram_id}")

        except TelegramError as e:
            logger.error(f"Помилка Telegram при надсиланні {reminder.id}: {e}")
        except Exception as e:
            logger.error(f"Помилка обробки нагадування {reminder.id}: {e}")

    logger.info(f"Надіслано {sent_count} нагадувань")
    return sent_count
