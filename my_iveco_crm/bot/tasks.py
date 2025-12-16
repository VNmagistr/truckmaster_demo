# bot/tasks.py
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from telegram import Bot
from telegram.error import TelegramError
import os

from .models import BotUser, ReminderSettings, SentReminder
from orders.models import ServiceOrder
from clients.models import Truck

logger = logging.getLogger(__name__)
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')


@shared_task
def send_daily_reminders():
    """Щоденна перевірка та відправка нагадувань"""
    logger.info("Запуск щоденних нагадувань...")
    
    bot = Bot(token=BOT_TOKEN)
    today = timezone.now().date()
    
    # Отримуємо активні налаштування нагадувань
    active_reminders = ReminderSettings.objects.filter(
        is_enabled=True,
        bot_user__is_active=True,
        bot_user__is_blocked=False
    ).select_related('bot_user', 'truck')
    
    sent_count = 0
    
    for reminder in active_reminders:
        try:
            # Перевірка чи потрібно відправити нагадування
            should_send, message = check_if_reminder_needed(reminder)
            
            if should_send:
                # Відправляємо нагадування
                send_reminder_to_user(bot, reminder, message)
                sent_count += 1
                
        except Exception as e:
            logger.error(f"Помилка при обробці нагадування {reminder.id}: {e}")
    
    logger.info(f"Відправлено {sent_count} нагадувань")
    return sent_count


@shared_task
def check_maintenance_reminders():
    """Перевірка нагадувань про ТО та обслуговування"""
    logger.info("Перевірка нагадувань про ТО...")
    
    bot = Bot(token=BOT_TOKEN)
    
    # Нагадування про ТО (за пробігом)
    reminders = ReminderSettings.objects.filter(
        reminder_type='maintenance',
        is_enabled=True,
        advance_km__gt=0,
        bot_user__is_active=True
    ).select_related('bot_user', 'truck')
    
    for reminder in reminders:
        try:
            truck = reminder.truck
            if not truck:
                continue
            
            # Останнє ТО
            last_service = ServiceOrder.objects.filter(
                truck=truck,
                status='completed'
            ).order_by('-created_at').first()
            
            if last_service and truck.mileage:
                # Приблизний пробіг з останнього ТО (якщо є дані)
                # Тут можна додати логіку розрахунку
                pass
                
        except Exception as e:
            logger.error(f"Помилка перевірки ТО: {e}")


def check_if_reminder_needed(reminder: ReminderSettings) -> tuple[bool, str]:
    """Перевірка чи потрібно відправити нагадування"""
    
    truck = reminder.truck
    if not truck:
        return False, ""
    
    # Перевірка чи не відправляли нагадування недавно
    recent_reminder = SentReminder.objects.filter(
        bot_user=reminder.bot_user,
        truck=truck,
        reminder_type=reminder.reminder_type,
        sent_at__gte=timezone.now() - timedelta(days=reminder.repeat_days or 7)
    ).exists()
    
    if recent_reminder:
        return False, ""
    
    # Різні типи нагадувань
    if reminder.reminder_type == 'maintenance':
        return check_maintenance_reminder(reminder)
    
    elif reminder.reminder_type == 'inspection':
        return check_inspection_reminder(reminder)
    
    elif reminder.reminder_type == 'custom':
        return check_custom_reminder(reminder)
    
    return False, ""


def check_maintenance_reminder(reminder: ReminderSettings) -> tuple[bool, str]:
    """Перевірка нагадування про ТО"""
    truck = reminder.truck
    
    # Останнє завершене замовлення на ТО
    last_maintenance = ServiceOrder.objects.filter(
        truck=truck,
        status='completed'
    ).order_by('-created_at').first()
    
    if not last_maintenance:
        # Немає історії ТО
        return False, ""
    
    days_since = (timezone.now().date() - last_maintenance.created_at.date()).days
    
    # Якщо минуло багато часу з останнього ТО
    if days_since >= 180:  # 6 місяців
        if reminder.advance_days and days_since >= (180 - reminder.advance_days):
            message = (
                f"🔔 Нагадування про ТО\n\n"
                f"Автомобіль: {truck.license_plate}\n"
                f"Останнє ТО: {last_maintenance.created_at.strftime('%d.%m.%Y')}\n"
                f"Днів тому: {days_since}\n\n"
                f"⚠️ Рекомендуємо записатися на технічне обслуговування!"
            )
            return True, message
    
    return False, ""


def check_inspection_reminder(reminder: ReminderSettings) -> tuple[bool, str]:
    """Перевірка нагадування про техогляд"""
    truck = reminder.truck
    
    # Тут можна додати логіку перевірки дати техогляду
    # Якщо в моделі Truck є поле inspection_date
    
    return False, ""


def check_custom_reminder(reminder: ReminderSettings) -> tuple[bool, str]:
    """Перевірка custom нагадування"""
    
    # Custom нагадування з specific_date
    if hasattr(reminder, 'specific_date') and reminder.specific_date:
        days_until = (reminder.specific_date - timezone.now().date()).days
        
        if days_until <= reminder.advance_days:
            message = (
                f"🔔 Нагадування\n\n"
                f"Автомобіль: {reminder.truck.license_plate}\n"
                f"Дата: {reminder.specific_date.strftime('%d.%m.%Y')}\n"
                f"Днів залишилось: {days_until}\n\n"
                f"Не забудьте!"
            )
            return True, message
    
    return False, ""


def send_reminder_to_user(bot: Bot, reminder: ReminderSettings, message: str):
    """Відправка нагадування користувачу"""
    try:
        bot.send_message(
            chat_id=reminder.bot_user.telegram_id,
            text=message
        )
        
        # Зберігаємо відправлене нагадування
        SentReminder.objects.create(
            bot_user=reminder.bot_user,
            truck=reminder.truck,
            reminder_type=reminder.reminder_type,
            message_text=message,
            is_delivered=True
        )
        
        logger.info(f"Нагадування відправлено користувачу {reminder.bot_user.telegram_id}")
        
    except TelegramError as e:
        logger.error(f"Помилка відправки в Telegram: {e}")
        
        # Зберігаємо невдалу спробу
        SentReminder.objects.create(
            bot_user=reminder.bot_user,
            truck=reminder.truck,
            reminder_type=reminder.reminder_type,
            message_text=message,
            is_delivered=False,
            delivery_error=str(e)
        )


@shared_task
def send_reminder_to_user_by_id(bot_user_id: int, message: str):
    """Відправка разового нагадування конкретному користувачу"""
    try:
        bot_user = BotUser.objects.get(id=bot_user_id)
        bot = Bot(token=BOT_TOKEN)
        
        bot.send_message(
            chat_id=bot_user.telegram_id,
            text=message
        )
        
        logger.info(f"Нагадування відправлено користувачу {bot_user.telegram_id}")
        return True
        
    except Exception as e:
        logger.error(f"Помилка відправки нагадування: {e}")
        return False