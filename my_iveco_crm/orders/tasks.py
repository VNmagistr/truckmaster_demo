import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def auto_close_done_orders():
    """
    Автоматично закриває наряди зі статусом DONE,
    якщо вони більше тижня не були переведені в CLOSED.
    """
    from .models import ServiceOrder

    threshold = timezone.now() - timedelta(weeks=1)

    orders = ServiceOrder.objects.filter(
        status=ServiceOrder.StatusChoices.DONE,
        marked_for_deletion=False,
    ).select_related('truck')

    # Фільтруємо по даті останнього переходу в DONE через OrderStatusHistory
    closed_ids = []
    for order in orders:
        last_done = order.status_history.filter(
            to_status=ServiceOrder.StatusChoices.DONE
        ).order_by('-changed_at').first()

        if last_done and last_done.changed_at < threshold:
            try:
                order.status = ServiceOrder.StatusChoices.CLOSED
                order.intervals_snapshot = None
                order.save(update_fields=['status', 'intervals_snapshot'])
                closed_ids.append(order.order_number)
            except Exception as e:
                logger.error(f"Авто-закриття: не вдалося закрити наряд {order.order_number}: {e}")

    if closed_ids:
        logger.info(f"Авто-закрито {len(closed_ids)} нарядів: {', '.join(closed_ids)}")
    else:
        logger.debug("Авто-закриття: нарядів для закриття не знайдено")

    return len(closed_ids)

@shared_task
def send_photo_notification_telegram(telegram_chat_id, text):
    import asyncio
    import os
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return
    try:
        from telegram import Bot
        bot = Bot(token=bot_token)
        asyncio.run(bot.send_message(
            chat_id=telegram_chat_id,
            text=text,
            parse_mode='Markdown',
        ))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'send_photo_notification_telegram error: {e}')
