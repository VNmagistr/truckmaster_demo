"""
Імпорт вантажівок та власників з .fp3 файлів (FastReport XML) у CRM.

Структура fp3 (FastReport):
  Блок b9  → власник: один елемент містить "Ім'я\r\nТелефон"
  Блок b11 → дані авто: після елемента "Модель:" йдуть:
               [0] модель (наприклад: 70C17, Stralis)
               [1] держномер (наприклад: ВС1657ОМ)
               [2] шасі (7 цифр, >4 000 000) або пробіг (<2 000 000)
               [3] пробіг (якщо [2] був шасі)

ВАЖЛИВО: номери m-тегів відрізняються між версіями шаблону,
тому парсинг робиться за позицією/вмістом, а не за назвою тега.

Використання:
    python manage.py import_fp3_to_crm <шлях_до_папки>
    python manage.py import_fp3_to_crm /path/fp3 --dry-run
    python manage.py import_fp3_to_crm /path/fp3 --verbose
"""

import re
from pathlib import Path
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand
from django.db import transaction

from clients.models import Client, Truck, IvecoBaseModel


# ──────────────────────────────────────────────────────────
# Допоміжні функції
# ──────────────────────────────────────────────────────────

_SKIP_RE = re.compile(
    r'^(Рахунок|від\s|Модель|Держ|Шасі|Пробіг|Постачальник|Одержувач|Платник)',
    re.IGNORECASE | re.UNICODE
)


def is_label(val):
    """True якщо це службовий рядок-мітка, а не дані."""
    return bool(_SKIP_RE.match(val))


def normalize_phone(raw):
    """
    Нормалізує номер телефону до формату +380XXXXXXXXX.
      +380XXXXXXXXX  → як є
      380XXXXXXXXX   → +
      0XXXXXXXXX     → +38
      80XXXXXXXXXX   → +3   (11 цифр з 8)
    """
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


def parse_client_block(raw):
    """
    Розбирає блок власника "Ім'я, м. Місто\r\nТелефон"
    → (name, phone)
    """
    if not raw:
        return None, None
    lines = [l.strip() for l in re.split(r'[\r\n]+', raw) if l.strip()]
    name_line = lines[0] if lines else ''
    phone_line = lines[1] if len(lines) > 1 else ''
    # Відрізаємо місто: "Іванов Іван, м. Львів" → "Іванов Іван"
    name = re.sub(r',\s*м\..*$', '', name_line).strip()[:255]
    phone = normalize_phone(phone_line) or normalize_phone(name_line)
    return name or None, phone


def make_vin(chassis):
    """Сурогатний VIN (17 символів) із 7-значного коду шасі."""
    return f'IMPORT{chassis:0>11}'


def vin_from_plate(plate):
    """Сурогатний VIN із держномера (якщо шасі відсутнє)."""
    key = re.sub(r'[^A-Z0-9А-ЯІЇЄ]', '', plate.upper())[:11]
    return f'PLATE{key:0<12}'[:17]


# ──────────────────────────────────────────────────────────
# Команда
# ──────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Імпортує вантажівки та власників з .fp3 файлів у CRM'

    def add_arguments(self, parser):
        parser.add_argument('fp3_folder', type=str, help='Шлях до папки з .fp3 файлами')
        parser.add_argument('--dry-run', action='store_true', help='Тільки показати, нічого не зберігати')
        parser.add_argument('--verbose', action='store_true', help='Детальний вивід по кожному файлу')

    def handle(self, *args, **options):
        folder = Path(options['fp3_folder'])
        dry_run = options['dry_run']
        verbose = options['verbose']

        if not folder.exists():
            self.stdout.write(self.style.ERROR(f'Папка не знайдена: {folder}'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  РЕЖИМ ПЕРЕВІРКИ — нічого не збережеться\n'))

        fp3_files = sorted(list(folder.glob('*.fp3')) + list(folder.glob('*.FP3')))
        if not fp3_files:
            self.stdout.write(self.style.WARNING('Не знайдено .fp3 файлів'))
            return

        self.stdout.write(f'Знайдено файлів: {len(fp3_files)}\n')

        stats = {
            'total': len(fp3_files),
            'parsed': 0,
            'skipped_no_plate': 0,
            'errors': 0,
            'clients_created': 0,
            'clients_found': 0,
            'trucks_created': 0,
            'trucks_found': 0,
            'trucks_linked': 0,
        }

        for idx, fp3_file in enumerate(fp3_files, 1):
            try:
                data = self._parse_fp3(fp3_file)
            except Exception as e:
                stats['errors'] += 1
                if verbose:
                    self.stdout.write(self.style.ERROR(
                        f'[{idx}/{stats["total"]}] Помилка парсингу {fp3_file.name}: {e}'
                    ))
                continue

            if not data:
                stats['errors'] += 1
                continue

            if not data.get('license_plate'):
                stats['skipped_no_plate'] += 1
                if verbose:
                    self.stdout.write(self.style.WARNING(
                        f'[{idx}/{stats["total"]}] Пропущено (немає держномера): {fp3_file.name}'
                    ))
                continue

            stats['parsed'] += 1

            if verbose:
                self.stdout.write(
                    f'\n[{idx}/{stats["total"]}] {fp3_file.name}\n'
                    f'  Держномер: {data["license_plate"]} | Модель: {data["model"]} | '
                    f'Шасі: {data["chassis"]} | Пробіг: {data["mileage"]}\n'
                    f'  Власник: {data["client_name"]} | Тел: {data["client_phone"]}'
                )

            if dry_run:
                continue

            try:
                with transaction.atomic():
                    client, client_created = self._get_or_create_client(data)
                    truck, truck_created, linked = self._get_or_create_truck(data, client)

                    if client_created:
                        stats['clients_created'] += 1
                    else:
                        stats['clients_found'] += 1
                    if truck_created:
                        stats['trucks_created'] += 1
                    else:
                        stats['trucks_found'] += 1
                    if linked:
                        stats['trucks_linked'] += 1

                    if verbose:
                        c_tag = '✨ новий' if client_created else '✅ знайдений'
                        t_tag = ('✨ нова' if truck_created
                                 else '🔗 оновлена' if linked else '✅ знайдена')
                        self.stdout.write(
                            f'  Клієнт [{c_tag}]: {client.name} (id={client.id})\n'
                            f'  Вантажівка [{t_tag}]: {truck.license_plate} (id={truck.id})'
                        )
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(
                    f'[{idx}/{stats["total"]}] Помилка збереження {fp3_file.name}: {e}'
                ))

            if not verbose and idx % 50 == 0:
                self.stdout.write(f'  Оброблено: {idx}/{stats["total"]}...')

        self._print_summary(stats, dry_run)

    # ──────────────────────────────────────────────────────
    # Парсинг fp3
    # ──────────────────────────────────────────────────────

    def _parse_fp3(self, fp3_path):
        """
        Парсить fp3 XML. Повертає словник або None при критичній помилці.

        Алгоритм для b11 (дані авто):
          1. Знаходимо елемент "Модель:" (мітка)
          2. Наступний після нього елемент = модель (завжди)
          3. Наступний = держномер (перший нечисловий нелейбловий)
          4. Числові елементи далі:
               7 цифр і число > 4 000 000 → шасі
               число < 2 000 000          → пробіг
        """
        raw = fp3_path.read_bytes()
        root = None
        for enc in ('utf-8', 'cp1251', 'utf-8-sig'):
            try:
                root = ET.fromstring(raw.decode(enc))
                break
            except (UnicodeDecodeError, ET.ParseError):
                continue
        if root is None:
            return None

        page0 = root.find('.//page0')
        if page0 is None:
            return None

        data = {
            'filename': fp3_path.name,
            'license_plate': None,
            'model': None,
            'chassis': None,
            'mileage': None,
            'client_name': None,
            'client_phone': None,
        }

        # ── Клієнт з b9 ──────────────────────────────────
        b9 = page0.find('.//b9')
        if b9 is not None:
            for elem in b9:
                val = elem.attrib.get('u', '')
                if '\r\n' in val or '\n' in val:
                    name, phone = parse_client_block(val)
                    if name:
                        data['client_name'] = name
                    if phone:
                        data['client_phone'] = phone
                    break

        # ── Дані авто з b11 ──────────────────────────────
        b11 = page0.find('.//b11')
        if b11 is not None:
            # Зібрати всі непорожні значення в порядку XML
            elems = [e.attrib.get('u', '').strip() for e in b11]
            elems = [v for v in elems if v]

            # Знаходимо індекс мітки "Модель:"
            model_label_idx = None
            for i, v in enumerate(elems):
                if v.startswith('Модель') and len(v) < 10:
                    model_label_idx = i
                    break

            if model_label_idx is not None:
                after = elems[model_label_idx + 1:]
                # [0] = модель
                if after:
                    data['model'] = after[0][:100]
                # [1] = держномер (перший нелейбловий нечисловий після моделі)
                plate_found = False
                for v in after[1:]:
                    if is_label(v):
                        continue
                    v_clean = re.sub(r'\s', '', v)
                    # Числові елементи → шасі або пробіг
                    if v_clean.isdigit():
                        num = int(v_clean)
                        if len(v_clean) == 7 and num > 4_000_000 and not data['chassis']:
                            data['chassis'] = v_clean
                        elif num < 2_000_000 and not data['mileage']:
                            data['mileage'] = num
                    elif not plate_found and not is_label(v):
                        # Перший нечисловий = держномер
                        data['license_plate'] = v[:20]
                        plate_found = True

        return data

    # ──────────────────────────────────────────────────────
    # Клієнт
    # ──────────────────────────────────────────────────────

    def _get_or_create_client(self, data):
        name = (data.get('client_name') or '').strip()
        phone = data.get('client_phone')

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

    # ──────────────────────────────────────────────────────
    # Вантажівка
    # ──────────────────────────────────────────────────────

    def _get_or_create_truck(self, data, client):
        """
        Повертає (truck, created, linked).
        linked=True якщо вантажівка вже існувала, але ми щойно прив'язали клієнта.
        """
        plate = data['license_plate']
        chassis = data.get('chassis')  # 7-значний рядок або None

        # 1. Шукаємо по держномеру
        truck = Truck.objects.filter(license_plate=plate).first()

        # 2. Якщо не знайдено — шукаємо по шасі (last_seven_vin)
        if truck is None and chassis:
            truck = Truck.objects.filter(last_seven_vin=chassis).first()

        if truck is not None:
            linked = False
            if client and truck.client_id != client.id:
                truck.client = client
                truck.save(update_fields=['client'])
                linked = True
            return truck, False, linked

        # 3. Створюємо нову вантажівку
        model_name = (data.get('model') or 'Невідома модель').strip()
        base_model, _ = IvecoBaseModel.objects.get_or_create(name=model_name)

        if chassis:
            full_vin = make_vin(chassis)
        else:
            full_vin = vin_from_plate(plate)

        # Вирішуємо колізію VIN (малоймовірна, але можлива)
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

    # ──────────────────────────────────────────────────────
    # Підсумок
    # ──────────────────────────────────────────────────────

    def _print_summary(self, stats, dry_run):
        self.stdout.write(self.style.SUCCESS(f'\n{"=" * 60}'))
        self.stdout.write(self.style.SUCCESS('Імпорт завершено:'))
        self.stdout.write(f'  Всього файлів:              {stats["total"]}')
        self.stdout.write(f'  Успішно розпарсено:         {stats["parsed"]}')
        self.stdout.write(self.style.WARNING(
            f'  Пропущено (немає номера):   {stats["skipped_no_plate"]}'
        ))
        if stats['errors']:
            self.stdout.write(self.style.ERROR(f'  Помилки:                    {stats["errors"]}'))
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
