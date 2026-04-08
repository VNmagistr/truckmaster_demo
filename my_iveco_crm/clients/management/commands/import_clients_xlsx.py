"""
Django management command: import clients and trucks from Excel file.

Usage:
    python manage.py import_clients_xlsx --file /path/to/БАЗА_2026.xlsx
    python manage.py import_clients_xlsx --file /path/to/БАЗА_2026.xlsx --dry-run

Expected columns (no header row):
    1  license_plate      e.g. АЕ8013РН
    2  last_seven_vin     e.g. 4374251  (ignored — auto-calculated from VIN)
    3  full_vin           e.g. WJMM1VSH404374251
    4  client_name        e.g. Трафік
    5  phone              e.g. +380504802277
    6  contact_person     (ignored)
    7  specific_model     e.g. 440S42 AS STRAL.2007
"""

import openpyxl
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Імпортує клієнтів та авто з Excel-файлу у базу CRM'

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True, help='Шлях до .xlsx файлу')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Тільки перегляд без запису в БД',
        )

    def handle(self, *args, **options):
        from clients.models import Client, Truck

        xlsx_path = options['file']
        dry_run   = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY-RUN: зміни в БД не зберігаються ==='))

        try:
            wb = openpyxl.load_workbook(xlsx_path)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'Файл не знайдено: {xlsx_path}'))
            return
        ws = wb.active

        stats = {
            'rows':              0,
            'skipped':           0,
            'clients_created':   0,
            'clients_updated':   0,
            'trucks_created':    0,
            'trucks_updated':    0,
            'ownership_changes': 0,
            'errors':            0,
        }

        # Попередньо збираємо телефони, що вже зайняті в БД
        # (phone unique=True — щоб не ловити IntegrityError в циклі)
        taken_phones = dict(
            Client.objects.exclude(phone__isnull=True)
                          .exclude(phone='')
                          .values_list('phone', 'name')
        )

        # Нормалізація імені клієнта для дедублікації
        def norm_name(s):
            return ' '.join(str(s).strip().split()).lower() if s else ''

        # Будуємо in-memory кеш уже оброблених клієнтів (у межах цього запуску)
        # key = norm_name → Client instance
        processed_clients: dict = {}

        for row_idx, row in enumerate(ws.iter_rows(min_row=1, values_only=True), start=1):
            stats['rows'] += 1

            license_plate = str(row[0]).strip() if row[0] else ''
            full_vin      = str(row[2]).strip() if row[2] else ''
            client_name   = str(row[3]).strip() if row[3] else ''
            phone_raw     = str(row[4]).strip() if row[4] else ''
            model_name    = str(row[6]).strip() if row[6] else ''

            # Пропускаємо порожні рядки
            if not client_name or not license_plate:
                self.stdout.write(f'  [рядок {row_idx}] пропускаємо: порожня назва або номер')
                stats['skipped'] += 1
                continue

            # Нормалізуємо телефон
            phone = phone_raw if phone_raw.startswith('+') else (
                '+38' + phone_raw.lstrip('0') if phone_raw else ''
            )
            if phone == '+38':
                phone = ''

            try:
                with transaction.atomic():
                    # ── КЛІЄНТ ──────────────────────────────────────────────
                    key = norm_name(client_name)
                    client = processed_clients.get(key)

                    if client is None:
                        # Шукаємо в БД (case-insensitive)
                        client = Client.objects.filter(
                            name__iexact=client_name
                        ).first()

                    client_updated = False
                    if client is None:
                        # Перевіряємо, чи не зайнятий телефон
                        safe_phone = None
                        if phone:
                            if phone in taken_phones:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'  [рядок {row_idx}] телефон {phone} вже у '
                                        f'"{taken_phones[phone]}", клієнт "{client_name}" '
                                        f'буде створений без телефону'
                                    )
                                )
                            else:
                                safe_phone = phone
                                taken_phones[phone] = client_name

                        if not dry_run:
                            client = Client.objects.create(
                                name=client_name,
                                phone=safe_phone or None,
                            )
                        else:
                            # Заглушка для dry-run — всі атрибути які можуть читатись нижче
                            class _FakeClient:
                                id = None
                                phone = safe_phone
                            _FakeClient.name = client_name
                            client = _FakeClient()
                        stats['clients_created'] += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'  [рядок {row_idx}] КЛІЄНТ створено: {client_name}')
                        )
                    else:
                        # Оновлюємо телефон якщо потрібно
                        if phone and not client.phone:
                            if phone not in taken_phones or taken_phones[phone] == norm_name(client.name):
                                if not dry_run:
                                    client.phone = phone
                                    client.save(update_fields=['phone'])
                                taken_phones[phone] = client.name
                                client_updated = True
                        if client_updated:
                            stats['clients_updated'] += 1
                            self.stdout.write(f'  [рядок {row_idx}] клієнт оновлено: {client_name}')

                    processed_clients[key] = client

                    # ── АВТО ─────────────────────────────────────────────────
                    truck = None
                    match_field = None

                    # Пошук: спочатку по VIN, потім по номерному знаку
                    if full_vin and len(full_vin) == 17:
                        truck = Truck.objects.filter(full_vin=full_vin).first()
                        match_field = 'VIN'

                    if truck is None and license_plate:
                        truck = Truck.objects.filter(
                            license_plate__iexact=license_plate
                        ).first()
                        match_field = 'license_plate'

                    if truck is None:
                        # Створюємо нове авто
                        vin = full_vin if len(full_vin) == 17 else None

                        if vin is None and not dry_run:
                            # VIN некоректний — пропускаємо авто, але не клієнта
                            self.stdout.write(
                                self.style.WARNING(
                                    f'  [рядок {row_idx}] VIN "{full_vin}" некоректний (≠17 символів) — '
                                    f'авто {license_plate} пропускаємо'
                                )
                            )
                            stats['skipped'] += 1
                            continue

                        if not dry_run and client.id:
                            # Перевіряємо унікальність VIN перед створенням
                            if vin and Truck.objects.filter(full_vin=vin).exists():
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'  [рядок {row_idx}] VIN {vin} вже існує — '
                                        f'авто {license_plate} пропускаємо'
                                    )
                                )
                                stats['skipped'] += 1
                                continue

                            Truck.objects.create(
                                client=client,
                                license_plate=license_plate,
                                full_vin=vin or 'UNKNOWN00000000' + str(row_idx).zfill(2),
                                specific_model_name=model_name or 'Невідомо',
                            )
                        stats['trucks_created'] += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  [рядок {row_idx}] АВТО створено: {license_plate} / {full_vin}'
                            )
                        )
                    else:
                        # Оновлюємо авто
                        from clients.models import OwnershipHistory
                        changed = {}

                        if license_plate and truck.license_plate != license_plate:
                            changed['license_plate'] = license_plate
                        if full_vin and len(full_vin) == 17 and truck.full_vin != full_vin:
                            changed['full_vin'] = full_vin
                        if model_name and truck.specific_model_name != model_name:
                            changed['specific_model_name'] = model_name

                        # ── Зміна власника ─────────────────────────────────
                        owner_changed = client.id and truck.client_id != client.id
                        if owner_changed:
                            old_owner_name = truck.client.name if truck.client else '—'
                            self.stdout.write(
                                self.style.WARNING(
                                    f'  [рядок {row_idx}] ЗМІНА ВЛАСНИКА: '
                                    f'"{old_owner_name}" → "{client_name}" '
                                    f'({truck.license_plate} / {truck.full_vin})'
                                )
                            )
                            if not dry_run:
                                # Записуємо старого власника в OwnershipHistory
                                OwnershipHistory.objects.create(
                                    truck=truck,
                                    client=truck.client,
                                    license_plate=truck.license_plate,
                                )
                            changed['client'] = client
                            stats['ownership_changes'] = stats.get('ownership_changes', 0) + 1

                        if changed:
                            if not dry_run:
                                for field, val in changed.items():
                                    setattr(truck, field, val)
                                truck.save(update_fields=list(changed.keys()))
                            stats['trucks_updated'] += 1
                            if not owner_changed:
                                self.stdout.write(
                                    f'  [рядок {row_idx}] авто оновлено ({match_field}): '
                                    f'{license_plate} — {list(changed.keys())}'
                                )

            except Exception as exc:
                stats['errors'] += 1
                self.stderr.write(
                    self.style.ERROR(f'  [рядок {row_idx}] ПОМИЛКА: {exc}')
                )

        # Підсумок
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write(f"Оброблено рядків:      {stats['rows']}")
        self.stdout.write(f"Пропущено:             {stats['skipped']}")
        self.stdout.write(f"Клієнтів створено:     {stats['clients_created']}")
        self.stdout.write(f"Клієнтів оновлено:     {stats['clients_updated']}")
        self.stdout.write(f"Авто створено:         {stats['trucks_created']}")
        self.stdout.write(f"Авто оновлено:         {stats['trucks_updated']}")
        self.stdout.write(
            self.style.WARNING(f"Змін власника:         {stats['ownership_changes']}")
            if stats['ownership_changes'] else
            f"Змін власника:         0"
        )
        self.stdout.write(f"Помилок:               {stats['errors']}")
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY-RUN: нічого не збережено'))
