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
            order.status = ServiceOrder.StatusChoices.CLOSED
            # Знімок більше не потрібен — наряд закривається
            order.intervals_snapshot = None
            order.save(update_fields=['status', 'intervals_snapshot'])
            closed_ids.append(order.order_number)

    if closed_ids:
        logger.info(f"Авто-закрито {len(closed_ids)} нарядів: {', '.join(closed_ids)}")
    else:
        logger.debug("Авто-закриття: нарядів для закриття не знайдено")

    return len(closed_ids)
