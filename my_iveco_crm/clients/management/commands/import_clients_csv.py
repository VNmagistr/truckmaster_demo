"""
Імпорт клієнтів зі старої бази (Firebird) у Django CRM.

Використання:
    python manage.py import_clients_csv /path/to/clients.csv
    python manage.py import_clients_csv /path/to/clients.csv --dry-run
    python manage.py import_clients_csv /path/to/clients.csv --skip-duplicates
"""

import csv
import re
from django.core.management.base import BaseCommand
from clients.models import Client


def clean_phone(raw):
    """
    Витягує перший придатний номер телефону з рядка.
    Приклади вхідних даних:
      'тел.(0332)786558, 80506271072'
      '+380954968071'
      '0673696268'
    """
    if not raw:
        return None

    # Видаляємо все крім цифр, +, (, )
    parts = re.split(r'[,;/\s]+', raw.strip())

    for part in parts:
        digits = re.sub(r'[^\d+]', '', part)
        if not digits:
            continue

        # Нормалізуємо до +38XXXXXXXXXX
        if digits.startswith('380') and len(digits) >= 12:
            return '+' + digits[:12]
        if digits.startswith('+380') and len(digits) >= 13:
            return digits[:13]
        if digits.startswith('80') and len(digits) >= 11:
            return '+3' + digits[:11]
        if digits.startswith('0') and len(digits) >= 10:
            return '+38' + digits[:10]
        # Короткий формат (0332)786558 → 0332786558
        if len(digits) >= 7:
            if not digits.startswith('0') and not digits.startswith('+'):
                digits = '0' + digits
            if digits.startswith('0') and len(digits) >= 10:
                return '+38' + digits[:10]

    return None


def clean_email(raw):
    """Перевіряє чи схожий рядок на email."""
    if not raw:
        return None
    raw = raw.strip().lower()
    if re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', raw):
        return raw
    return None


def build_name(firma_flag, fio, firma):
    """
    У старій базі:
      firma=1 → юридична особа, fio містить назву компанії
      firma=0 → фізична особа, fio містить ПІБ
    """
    name = (fio or firma or '').strip()
    return name if name else 'Без назви'


class Command(BaseCommand):
    help = 'Імпортує клієнтів з clients.csv у базу CRM'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_path',
            type=str,
            help='Шлях до файлу clients.csv'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Тільки показати що буде імпортовано, не зберігати'
        )
        parser.add_argument(
            '--skip-duplicates',
            action='store_true',
            default=True,
            help='Пропускати клієнтів з телефоном що вже існує (за замовчуванням увімкнено)'
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        dry_run = options['dry_run']
        skip_duplicates = options['skip_duplicates']

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  РЕЖИМ ПЕРЕВІРКИ — нічого не збережеться\n'))

        stats = {
            'total': 0,
            'created': 0,
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

                name = build_name(
                    row.get('firma', '0'),
                    row.get('fio', ''),
                    row.get('firma', '')
                )

                if not name or name == 'Без назви':
                    stats['skipped_empty'] += 1
                    continue

                phone = clean_phone(row.get('tel', ''))
                email = clean_email(row.get('email', ''))
                address = (row.get('adr') or row.get('adr_ur') or '').strip()[:255]
                notes = row.get('notes', '').strip()

                # Додаємо ЄДРПОУ в notes якщо є
                inn = row.get('inn', '').strip()
                if inn:
                    notes = f"ЄДРПОУ/ІПН: {inn}" + (f". {notes}" if notes else '')

                # Перевірка унікальності телефону
                if phone and Client.objects.filter(phone=phone).exists():
                    if skip_duplicates:
                        stats['skipped_duplicate'] += 1
                        self.stdout.write(
                            self.style.WARNING(f'  [пропущено] {name} — телефон {phone} вже існує')
                        )
                        continue

                # Перевірка унікальності імені (щоб не дублювати)
                if Client.objects.filter(name=name).exists():
                    stats['skipped_duplicate'] += 1
                    self.stdout.write(
                        self.style.WARNING(f'  [пропущено] {name} — клієнт з таким іменем вже існує')
                    )
                    continue

                if dry_run:
                    self.stdout.write(
                        f'  [буде створено] {name} | тел: {phone or "—"} | email: {email or "—"}'
                    )
                    stats['created'] += 1
                    continue

                try:
                    Client.objects.create(
                        name=name,
                        phone=phone,
                        email=email,
                        address=address or None,
                    )
                    stats['created'] += 1
                except Exception as e:
                    stats['errors'] += 1
                    self.stdout.write(
                        self.style.ERROR(f'  [помилка] {name} (рядок id={row_id}): {e}')
                    )

        # Підсумок
        self.stdout.write(self.style.SUCCESS(f'\n{"="*50}'))
        self.stdout.write(self.style.SUCCESS(f'Імпорт завершено:'))
        self.stdout.write(f'  Всього у файлі:       {stats["total"]}')
        self.stdout.write(self.style.SUCCESS(f'  Створено:             {stats["created"]}'))
        self.stdout.write(self.style.WARNING(f'  Пропущено (дублі):    {stats["skipped_duplicate"]}'))
        self.stdout.write(f'  Пропущено (порожні):  {stats["skipped_empty"]}')
        if stats['errors']:
            self.stdout.write(self.style.ERROR(f'  Помилки:              {stats["errors"]}'))
        self.stdout.write(self.style.SUCCESS(f'{"="*50}'))
