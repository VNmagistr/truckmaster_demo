import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def send_staff_telegram_task(arrival_id):
    try:
        from alpr.models import VehicleArrival
        arrival = VehicleArrival.objects.select_related(
            'client', 'truck', 'appointment'
        ).get(pk=arrival_id)
    except Exception as e:
        logger.error(f'send_staff_telegram_task: arrival {arrival_id} not found: {e}')
        return

    from alpr.notifications import send_staff_telegram
    send_staff_telegram(arrival)
