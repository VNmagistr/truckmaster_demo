"""
Імпорт запчастин зі старої бази (Firebird) у Django CRM.

Використання:
    python manage.py import_products_csv /path/to/products.csv
    python manage.py import_products_csv /path/to/products.csv --dry-run
    python manage.py import_products_csv /path/to/products.csv --with-services
"""

import csv
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from inventory.models import Product


# Маппінг одиниць виміру зі старої бази на Django-choices
UNIT_MAP = {
    'шт':      'pcs',
    'шт.':     'pcs',
    'компл.':  'pcs',
    'блок':    'pcs',
    'л':       'l',
    'л.':      'l',
    'мл':      'l',
    'кг':      'kg',
    'г':       'kg',
    'м':       'm',
    'м.':      'm',
}

# Одиниці що означають послугу — пропускаємо
SERVICE_UNITS = {'годин', 'год', 'год.', 'посл.', 'послуга'}


def map_unit(raw):
    raw = (raw or '').strip()
    if raw in SERVICE_UNITS:
        return None  # сигнал що це послуга
    return UNIT_MAP.get(raw, 'pcs')


def to_decimal(val, default=0):
    try:
        return Decimal(str(val)).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


class Command(BaseCommand):
    help = 'Імпортує запчастини з products.csv у базу CRM'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_path',
            type=str,
            help='Шлях до файлу products.csv'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Тільки показати що буде імпортовано, не зберігати'
        )
        parser.add_argument(
            '--with-services',
            action='store_true',
            help='Також імпортувати послуги (за замовчуванням пропускаються)'
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        dry_run = options['dry_run']
        with_services = options['with_services']

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  РЕЖИМ ПЕРЕВІРКИ — нічого не збережеться\n'))

        stats = {
            'total': 0,
            'created': 0,
            'skipped_service': 0,
            'skipped_duplicate': 0,
            'skipped_empty': 0,
            'errors': 0,
        }

        try:
            f = open(csv_path, encoding='utf-8-sig', newline='')
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл не знайдено: {csv_path}'))
            return

        with f:
            reader = csv.DictReader(f)

            for row in reader:
                stats['total'] += 1
                row_id = row.get('id', '?')

                name = (row.get('name') or '').strip()[:255]
                if not name:
                    stats['skipped_empty'] += 1
                    continue

                is_service_flag = row.get('is_service', 'ні') == 'так'
                unit_raw = row.get('unit', '').strip()
                unit = map_unit(unit_raw)

                # Пропускаємо послуги якщо не передано --with-services
                if (is_service_flag or unit is None) and not with_services:
                    stats['skipped_service'] += 1
                    continue

                if unit is None:
                    unit = 'pcs'

                # Артикул: якщо порожній — генеруємо з id
                sku = (row.get('sku') or '').strip()[:100]
                if not sku:
                    sku = f'IMPORT-{row_id}'

                # Перевірка унікальності артикулу
                if Product.objects.filter(sku_code=sku).exists():
                    stats['skipped_duplicate'] += 1
                    self.stdout.write(
                        self.style.WARNING(f'  [пропущено] {name} — артикул "{sku}" вже існує')
                    )
                    continue

                cost_price    = to_decimal(row.get('cost_price', 0))
                selling_price = to_decimal(row.get('retail_price', 0))
                current_stock = to_decimal(row.get('stock', 0))
                brand         = (row.get('brand') or '').strip()[:100]
                notes         = (row.get('notes') or '').strip()

                if dry_run:
                    self.stdout.write(
                        f'  [буде створено] {name} | арт: {sku} | '
                        f'ціна: {selling_price} | залишок: {current_stock} {unit_raw}'
                    )
                    stats['created'] += 1
                    continue

                try:
                    Product.objects.create(
                        name=name,
                        sku_code=sku,
                        brand=brand,
                        unit=unit,
                        cost_price=cost_price,
                        selling_price=selling_price,
                        current_stock=current_stock,
                        notes=notes,
                        is_active=True,
                    )
                    stats['created'] += 1
                except Exception as e:
                    stats['errors'] += 1
                    self.stdout.write(
                        self.style.ERROR(f'  [помилка] {name} (id={row_id}): {e}')
                    )

        # Підсумок
        self.stdout.write(self.style.SUCCESS(f'\n{"="*50}'))
        self.stdout.write(self.style.SUCCESS('Імпорт завершено:'))
        self.stdout.write(f'  Всього у файлі:            {stats["total"]}')
        self.stdout.write(self.style.SUCCESS(f'  Створено:                  {stats["created"]}'))
        self.stdout.write(f'  Пропущено (послуги):       {stats["skipped_service"]}')
        self.stdout.write(self.style.WARNING(f'  Пропущено (дублі арт.):    {stats["skipped_duplicate"]}'))
        self.stdout.write(f'  Пропущено (без назви):     {stats["skipped_empty"]}')
        if stats['errors']:
            self.stdout.write(self.style.ERROR(f'  Помилки:                   {stats["errors"]}'))
        self.stdout.write(self.style.SUCCESS(f'{"="*50}'))
