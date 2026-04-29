"""Одноразовий бекфіл: для всіх BotUser з role='owner' і прив'язаним клієнтом
синхронізувати assigned_trucks із поточним client.truck_set.

До цієї міграції M2M assigned_trucks для власників заповнювалося лише при
прив'язці телефону і не оновлювалося, коли адмін додавав/змінював авто
клієнта — тому в адмінці видно лише знімок на момент реєстрації.
"""
from django.db import migrations


def backfill(apps, schema_editor):
    BotUser = apps.get_model('bot', 'BotUser')
    Truck = apps.get_model('clients', 'Truck')

    for bu in BotUser.objects.filter(role='owner').exclude(client__isnull=True):
        truck_ids = list(Truck.objects.filter(client_id=bu.client_id).values_list('id', flat=True))
        existing_ids = set(bu.assigned_trucks.values_list('id', flat=True))
        target_ids = set(truck_ids)
        to_add = target_ids - existing_ids
        to_remove = existing_ids - target_ids
        if to_add:
            bu.assigned_trucks.add(*to_add)
        if to_remove:
            bu.assigned_trucks.remove(*to_remove)


def noop_reverse(apps, schema_editor):
    # Зворотна міграція не відновить попередній знімок — просто нічого не робимо.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0005_unknown_plate_search'),
        ('clients', '0007_truck_transmission_type'),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]
