"""
Імпорт вантажівок та власників з CSV (підготовленого з fp3 файлів) у CRM.

CSV формат (utf-8-sig):
  license_plate, model, chassis, mileage, client_name, phone

Використання:
    python manage.py import_trucks_csv /path/to/trucks_from_fp3.csv
    python manage.py import_trucks_csv /path/to/trucks_from_fp3.csv --dry-run
"""

import csv
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from clients.models import Client, Truck, IvecoBaseModel


def normalize_phone(raw):
    if not raw:
        return None
    digits = re.sub(r'[^\d+]', '', raw.strip())
    if digits.startswith('+380') and len(digits) == 13:
        return digits
    if digits.startswith('380') and len(digits) == 12:
        return '+' + digits
    if digits.startswith('0') and len(digits) == 10:
        return '+38' + digits
    if digits.startswith('8') and len(digits) == 11:
        return '+3' + digits
    return None


def make_vin(chassis):
    """Сурогатний VIN (17 символів) із 7-значного шасі."""
    return f'IMPORT{chassis:0>11}'


def vin_from_plate(plate):
    """Сурогатний VIN із держномера (якщо шасі відсутнє)."""
    key = re.sub(r'[^A-Z0-9А-ЯІЇЄ]', '', plate.upper())[:11]
    return f'PLATE{key:0<12}'[:17]


class Command(BaseCommand):
    help = 'Імпортує вантажівки та власників з CSV у CRM'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Шлях до CSV файлу')
        parser.add_argument('--dry-run', action='store_true',
                            help='Тільки показати, нічого не зберігати')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '⚠️  РЕЖИМ ПЕРЕВІРКИ — нічого не збережеться\n'
            ))

        stats = {
            'total': 0,
            'skipped_no_plate': 0,
            'errors': 0,
            'clients_created': 0,
            'clients_found': 0,
            'trucks_created': 0,
            'trucks_found': 0,
            'trucks_linked': 0,
        }

        try:
            f = open(csv_path, encoding='utf-8-sig', newline='')
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл не знайдено: {csv_path}'))
            return

        with f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f'Всього рядків у CSV: {len(rows)}\n')

        for row in rows:
            stats['total'] += 1
            plate = (row.get('license_plate') or '').strip()[:20]
            if not plate:
                stats['skipped_no_plate'] += 1
                continue

            model_name = (row.get('model') or 'Невідома модель').strip()[:100]
            chassis = (row.get('chassis') or '').strip()
            client_name = (row.get('client_name') or '').strip()[:255]
            phone = normalize_phone(row.get('phone', ''))

            if dry_run:
                self.stdout.write(
                    f'  [буде] {plate} | {model_name} | шасі:{chassis} | '
                    f'власник:{client_name} | тел:{phone}'
                )
                continue

            try:
                with transaction.atomic():
                    # Клієнт
                    client = None
                    if phone or client_name:
                        client, client_created = self._get_or_create_client(
                            client_name, phone
                        )
                        if client_created:
                            stats['clients_created'] += 1
                        else:
                            stats['clients_found'] += 1

                    # Вантажівка
                    truck, truck_created, linked = self._get_or_create_truck(
                        plate, model_name, chassis, client
                    )
                    if truck_created:
                        stats['trucks_created'] += 1
                    else:
                        stats['trucks_found'] += 1
                    if linked:
                        stats['trucks_linked'] += 1

            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(
                    f'  [помилка] {plate}: {e}'
                ))

            if stats['total'] % 200 == 0:
                self.stdout.write(
                    f'  Оброблено: {stats["total"]}/{len(rows)}...'
                )

        self._print_summary(stats, dry_run)

    def _get_or_create_client(self, name, phone):
        # Шукаємо по телефону
        if phone:
            client = Client.objects.filter(phone=phone).first()
            if client:
                return client, False

        # Шукаємо по імені
        if name:
            client = Client.objects.filter(name__iexact=name).first()
            if client:
                if phone and not client.phone:
                    client.phone = phone
                    client.save(update_fields=['phone'])
                return client, False

        # Створюємо нового
        client = Client.objects.create(
            name=name or 'Невідомий власник',
            phone=phone,
        )
        return client, True

    def _get_or_create_truck(self, plate, model_name, chassis, client):
        """Повертає (truck, created, linked)."""
        # Шукаємо по номеру
        truck = Truck.objects.filter(license_plate=plate).first()

        # Якщо не знайдено — шукаємо по шасі
        if truck is None and chassis:
            truck = Truck.objects.filter(last_seven_vin=chassis).first()

        if truck is not None:
            linked = False
            if client and truck.client_id != client.id:
                truck.client = client
                truck.save(update_fields=['client'])
                linked = True
            return truck, False, linked

        # Створюємо нову
        base_model, _ = IvecoBaseModel.objects.get_or_create(name=model_name)

        if chassis:
            full_vin = make_vin(chassis)
        else:
            full_vin = vin_from_plate(plate)

        # Вирішуємо рідкісну колізію VIN
        if Truck.objects.filter(full_vin=full_vin).exists():
            suffix = re.sub(r'\D', '', plate)[-4:].zfill(4)
            full_vin = (full_vin[:13] + suffix).ljust(17, '0')[:17]

        truck = Truck.objects.create(
            client=client,
            base_model=base_model,
            specific_model_name=model_name,
            full_vin=full_vin,
            license_plate=plate,
        )
        return truck, True, False

    def _print_summary(self, stats, dry_run):
        self.stdout.write(self.style.SUCCESS(f'\n{"=" * 60}'))
        self.stdout.write(self.style.SUCCESS('Імпорт завершено:'))
        self.stdout.write(f'  Всього у файлі:             {stats["total"]}')
        self.stdout.write(self.style.WARNING(
            f'  Пропущено (немає номера):   {stats["skipped_no_plate"]}'
        ))
        if stats['errors']:
            self.stdout.write(self.style.ERROR(
                f'  Помилки:                    {stats["errors"]}'
            ))
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'  Клієнтів створено:          {stats["clients_created"]}'
            ))
            self.stdout.write(f'  Клієнтів знайдено:          {stats["clients_found"]}')
            self.stdout.write(self.style.SUCCESS(
                f'  Вантажівок створено:        {stats["trucks_created"]}'
            ))
            self.stdout.write(f'  Вантажівок знайдено:        {stats["trucks_found"]}')
            self.stdout.write(f'  Вантажівок прив\'язано:      {stats["trucks_linked"]}')
        self.stdout.write(self.style.SUCCESS(f'{"=" * 60}'))
