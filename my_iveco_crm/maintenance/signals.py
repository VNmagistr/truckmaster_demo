from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from .models import ServiceReminder

_status_cache = {}


def _get_interval_km(reminder: ServiceReminder):
    """
    Пріоритет джерел інтервалу за пробігом:
    1. Ручне перевизначення на самому нагадуванні (interval_km)
    2. MaintenanceKit конкретного авто (oil_change_interval_km)
    3. Дефолт типу ТО (ServiceType.default_interval_km)
    """
    if reminder.interval_km:
        return reminder.interval_km
    try:
        kit = reminder.truck.maintenancekit
        if kit.oil_change_interval_km:
            return kit.oil_change_interval_km
    except Exception:
        pass
    if reminder.service_type and reminder.service_type.default_interval_km:
        return reminder.service_type.default_interval_km
    return None


def _get_interval_months(reminder: ServiceReminder):
    """
    Пріоритет джерел часового інтервалу:
    1. Ручне перевизначення (interval_months)
    2. Дефолт типу ТО (ServiceType.default_interval_months)
    """
    if reminder.interval_months:
        return reminder.interval_months
    if reminder.service_type and reminder.service_type.default_interval_months:
        return reminder.service_type.default_interval_months
    return None


@receiver(pre_save, sender=ServiceReminder)
def cache_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            _status_cache[instance.pk] = ServiceReminder.objects.get(pk=instance.pk).status
        except ServiceReminder.DoesNotExist:
            pass


@receiver(post_save, sender=ServiceReminder)
def auto_create_next_reminder(sender, instance, created, **kwargs):
    """Після позначення нагадування як 'виконано' — автоматично створює наступне."""
    if created:
        return

    old_status = _status_cache.pop(instance.pk, None)

    if old_status == 'completed' or instance.status != 'completed':
        return

    interval_km = _get_interval_km(instance)
    interval_months = _get_interval_months(instance)

    if not interval_km and not interval_months:
        return

    # Не дублюємо якщо вже є активне нагадування для цього авто + типу ТО
    filters = dict(truck=instance.truck, status__in=['pending', 'notified'])
    if instance.service_type:
        filters['service_type'] = instance.service_type
    else:
        filters['title'] = instance.title

    if ServiceReminder.objects.filter(**filters).exists():
        return

    # Обчислюємо наступні цільові значення
    next_mileage = None
    if interval_km:
        if instance.completed_order and instance.completed_order.current_mileage:
            base_mileage = instance.completed_order.current_mileage
        else:
            base_mileage = instance.truck.get_latest_mileage()
        if base_mileage:
            next_mileage = base_mileage + interval_km

    next_date = None
    if interval_months:
        base_date = instance.completed_at.date() if instance.completed_at else timezone.now().date()
        next_date = base_date + relativedelta(months=interval_months)

    if not next_mileage and not next_date:
        return

    ServiceReminder.objects.create(
        truck=instance.truck,
        service_type=instance.service_type,
        title=instance.title,
        description=instance.description,
        reminder_type=instance.reminder_type,
        target_mileage=next_mileage,
        target_date=next_date,
        priority=instance.priority,
        notify_frequency_days=instance.notify_frequency_days,
        # interval_km і interval_months не копіюємо — наступного разу знову
        # підтягнеться з MaintenanceKit актуальне значення
        status='pending',
    )
