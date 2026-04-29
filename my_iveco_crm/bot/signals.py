"""Сигнали для автоматичної синхронізації BotUser.assigned_trucks з власником авто.

Поле `assigned_trucks` (M2M) — це історично знімок, який заповнювався один раз
при прив'язці телефону. Для власників (`role='owner'`) воно має відповідати
поточному `client.truck_set`. Сигнали нижче підтримують цей інваріант.
"""
import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from clients.models import Truck
from .models import BotUser

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Truck)
def sync_owners_on_truck_save(sender, instance, **kwargs):
    """Узгодити assigned_trucks для всіх BotUser-власників, на яких впливає авто.

    Викликається при будь-якій зміні авто (включно зі зміною клієнта).
    Додає авто новому власнику і прибирає у будь-якого власника, чий
    клієнт більше не відповідає поточному client авто.
    """
    try:
        if instance.client_id:
            for bu in BotUser.objects.filter(role='owner', client_id=instance.client_id):
                bu.assigned_trucks.add(instance)

        stale_owners = BotUser.objects.filter(role='owner', assigned_trucks=instance)
        if instance.client_id:
            stale_owners = stale_owners.exclude(client_id=instance.client_id)
        for bu in stale_owners:
            bu.assigned_trucks.remove(instance)
    except Exception as e:
        logger.error(f"sync_owners_on_truck_save failed for truck {instance.pk}: {e}")


@receiver(post_delete, sender=Truck)
def remove_truck_from_assigned(sender, instance, **kwargs):
    try:
        for bu in BotUser.objects.filter(assigned_trucks=instance):
            bu.assigned_trucks.remove(instance)
    except Exception as e:
        logger.error(f"remove_truck_from_assigned failed for truck {instance.pk}: {e}")


@receiver(post_save, sender=BotUser)
def refresh_owner_assigned_trucks(sender, instance, **kwargs):
    """Коли BotUser зберігається з role=owner і прив'язаним клієнтом —
    привести assigned_trucks у відповідність до client.truck_set."""
    if instance.role != 'owner' or not instance.client_id:
        return
    try:
        current_truck_ids = set(
            Truck.objects.filter(client_id=instance.client_id).values_list('id', flat=True)
        )
        existing_ids = set(instance.assigned_trucks.values_list('id', flat=True))
        to_add = current_truck_ids - existing_ids
        to_remove = existing_ids - current_truck_ids
        if to_add:
            instance.assigned_trucks.add(*to_add)
        if to_remove:
            instance.assigned_trucks.remove(*to_remove)
    except Exception as e:
        logger.error(f"refresh_owner_assigned_trucks failed for bot_user {instance.pk}: {e}")
