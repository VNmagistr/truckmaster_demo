"""
Django management command для імпорту даних з .fp3 файлів (FastReport XML) у CRM систему.

НОВІ ФУНКЦІЇ:
1. Збереження списку файлів з помилками у окремий файл
2. Детальне логування причин пропуску
3. Можливість повторного імпорту тільки файлів з помилками

Використання:
    python manage.py import_fp3_to_crm <path_to_fp3_folder> [опції]

Опції:
    --dry-run              Тестовий запуск без збереження в БД
    --retry-errors         Повторити імпорт файлів з помилками з попереднього запуску
    --error-log FILE       Шлях до файлу з помилками (за замовчуванням: fp3_errors.log)
    --skip-log FILE        Шлях до файлу з пропущеними (за замовчуванням: fp3_skipped.log)
    --verbose              Детальний вивід (показувати всі пропущені файли)

Приклади:
    # Перший імпорт з детальним логуванням
    python manage.py import_fp3_to_crm /path/to/fp3 --verbose
    
    # Повторити тільки файли з помилками
    python manage.py import_fp3_to_crm /path/to/fp3 --retry-errors
    
    # Тестовий запуск з іншими назвами логів
    python manage.py import_fp3_to_crm /path/to/fp3 --dry-run --error-log errors.txt
"""

import os
import re
import json
from decimal import Decimal
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import make_aware

from clients.models import Client, Truck, IvecoBaseModel
from orders.models import ServiceOrder, WorkPrice, WorkGroup, Part


class Command(BaseCommand):
    help = 'Імпортує дані з .fp3 файлів (FastReport XML) у CRM систему з детальним логуванням'

    def add_arguments(self, parser):
        parser.add_argument(
            'fp3_folder',
            type=str,
            help='Шлях до папки з .fp3 файлами'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Тестовий запуск без збереження в базу даних'
        )
        parser.add_argument(
            '--retry-errors',
            action='store_true',
            help='Повторити імпорт тільки файлів з помилками з попереднього запуску'
        )
        parser.add_argument(
            '--error-log',
            type=str,
            default='fp3_errors.log',
            help='Файл для збереження помилок (за замовчуванням: fp3_errors.log)'
        )
        parser.add_argument(
            '--skip-log',
            type=str,
            default='fp3_skipped.log',
            help='Файл для збереження пропущених файлів (за замовчуванням: fp3_skipped.log)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Детальний вивід (показувати всі пропущені файли)'
        )

    def handle(self, *args, **options):
        fp3_folder = options['fp3_folder']
        dry_run = options['dry_run']
        retry_errors = options['retry_errors']
        error_log_file = options['error_log']
        skip_log_file = options['skip_log']
        verbose = options['verbose']

        if not os.path.exists(fp3_folder):
            self.stdout.write(self.style.ERROR(f'Папка не існує: {fp3_folder}'))
            return

        # Ініціалізація логування
        self.error_log = []
        self.skip_log = []
        self.verbose = verbose

        if dry_run:
            self.stdout.write(self.style.WARNING('=' * 80))
            self.stdout.write(self.style.WARNING('ТЕСТОВИЙ РЕЖИМ (--dry-run)'))
            self.stdout.write(self.style.WARNING('Дані НЕ будуть збережені в базу даних'))
            self.stdout.write(self.style.WARNING('=' * 80))

        # Визначаємо список файлів для обробки
        if retry_errors:
            fp3_files = self.load_error_files(error_log_file, fp3_folder)
            if not fp3_files:
                self.stdout.write(self.style.WARNING(
                    f'Файл з помилками не знайдено або порожній: {error_log_file}'
                ))
                return
            self.stdout.write(self.style.WARNING(
                f'\n🔄 РЕЖИМ ПОВТОРУ: обробка {len(fp3_files)} файлів з помилками\n'
            ))
        else:
            fp3_files = list(Path(fp3_folder).glob('*.fp3'))
            if not fp3_files:
                self.stdout.write(self.style.WARNING(f'FP3 файли не знайдено в {fp3_folder}'))
                return

        self.stdout.write(f'\nЗнайдено FP3 файлів: {len(fp3_files)}\n')

        # Статистика
        stats = {
            'total': len(fp3_files),
            'success': 0,
            'errors': 0,
            'skipped': 0,
            'created': {
                'clients': 0,
                'trucks': 0,
                'orders': 0,
                'works': 0,
                'parts': 0
            }
        }

        # Обробка файлів
        for idx, fp3_file in enumerate(fp3_files, 1):
            if not verbose and idx % 100 == 0:
                self.stdout.write(f'Оброблено: {idx}/{len(fp3_files)}...')

            try:
                # Парсимо XML
                data = self.parse_fp3_file(fp3_file)
                
                if not data:
                    reason = "Не вдалося розпарсити XML"
                    self.log_skip(fp3_file, reason)
                    stats['skipped'] += 1
                    if verbose:
                        self.stdout.write(self.style.WARNING(
                            f'⚠️  [{idx}/{len(fp3_files)}] Пропущено: {fp3_file.name} - {reason}'
                        ))
                    continue

                # Перевіряємо обов'язкові поля
                if not data.get('license_plate'):
                    reason = "Відсутній держномер"
                    self.log_skip(fp3_file, reason, data)
                    stats['skipped'] += 1
                    if verbose:
                        self.stdout.write(self.style.WARNING(
                            f'⚠️  [{idx}/{len(fp3_files)}] Пропущено: {fp3_file.name} - {reason}'
                        ))
                    continue

                if verbose:
                    self.stdout.write(f'\n{"=" * 80}')
                    self.stdout.write(f'[{idx}/{len(fp3_files)}] Обробка: {fp3_file.name}')
                    self.print_extracted_data(data)

                if not dry_run:
                    # Імпортуємо в базу даних
                    created_counts = self.import_to_database(data)
                    
                    # Оновлюємо статистику створених об'єктів
                    for key, count in created_counts.items():
                        stats['created'][key] += count
                    
                    if verbose:
                        self.stdout.write(self.style.SUCCESS('✅ Успішно імпортовано'))

                stats['success'] += 1

            except Exception as e:
                error_msg = str(e)
                self.log_error(fp3_file, error_msg, data if 'data' in locals() else None)
                stats['errors'] += 1
                
                if verbose:
                    self.stdout.write(self.style.ERROR(
                        f'❌ [{idx}/{len(fp3_files)}] Помилка: {fp3_file.name} - {error_msg}'
                    ))
                    import traceback
                    self.stdout.write(self.style.ERROR(traceback.format_exc()))

        # Зберігаємо логи
        self.save_logs(error_log_file, skip_log_file, fp3_folder)

        # Підсумкова статистика
        self.print_summary(stats, dry_run, error_log_file, skip_log_file)

    def load_error_files(self, error_log_file, fp3_folder):
        """Завантаження списку файлів з помилками для повторної обробки"""
        if not os.path.exists(error_log_file):
            return []

        error_files = []
        with open(error_log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('FILE:'):
                    filename = line.replace('FILE:', '').strip()
                    filepath = Path(fp3_folder) / filename
                    if filepath.exists():
                        error_files.append(filepath)

        return error_files

    def log_error(self, fp3_file, error_msg, data=None):
        """Логування помилки"""
        log_entry = {
            'file': fp3_file.name,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        }
        if data:
            log_entry['data'] = {
                'license_plate': data.get('license_plate'),
                'invoice_number': data.get('invoice_number'),
                'client_name': data.get('client_name')
            }
        self.error_log.append(log_entry)

    def log_skip(self, fp3_file, reason, data=None):
        """Логування пропущеного файлу"""
        log_entry = {
            'file': fp3_file.name,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
        if data:
            log_entry['data'] = {
                'license_plate': data.get('license_plate'),
                'invoice_number': data.get('invoice_number'),
                'client_name': data.get('client_name')
            }
        self.skip_log.append(log_entry)

    def save_logs(self, error_log_file, skip_log_file, fp3_folder):
        """Збереження логів у файли"""
        # Збереження помилок
        if self.error_log:
            with open(error_log_file, 'w', encoding='utf-8') as f:
                f.write(f'# Файли з помилками імпорту\n')
                f.write(f'# Згенеровано: {datetime.now().isoformat()}\n')
                f.write(f'# Папка: {fp3_folder}\n')
                f.write(f'# Всього помилок: {len(self.error_log)}\n\n')
                
                for entry in self.error_log:
                    f.write(f'FILE: {entry["file"]}\n')
                    f.write(f'TIME: {entry["timestamp"]}\n')
                    f.write(f'ERROR: {entry["error"]}\n')
                    if 'data' in entry:
                        f.write(f'DATA: {json.dumps(entry["data"], ensure_ascii=False)}\n')
                    f.write('-' * 80 + '\n\n')

            self.stdout.write(self.style.WARNING(
                f'\n📝 Файли з помилками збережено в: {error_log_file}'
            ))

        # Збереження пропущених
        if self.skip_log:
            with open(skip_log_file, 'w', encoding='utf-8') as f:
                f.write(f'# Пропущені файли\n')
                f.write(f'# Згенеровано: {datetime.now().isoformat()}\n')
                f.write(f'# Папка: {fp3_folder}\n')
                f.write(f'# Всього пропущено: {len(self.skip_log)}\n\n')
                
                # Групуємо по причинах
                reasons = {}
                for entry in self.skip_log:
                    reason = entry['reason']
                    if reason not in reasons:
                        reasons[reason] = []
                    reasons[reason].append(entry)

                # Виводимо статистику по причинах
                f.write('СТАТИСТИКА ПО ПРИЧИНАХ:\n')
                for reason, entries in sorted(reasons.items(), key=lambda x: len(x[1]), reverse=True):
                    f.write(f'  {reason}: {len(entries)} файлів\n')
                f.write('\n' + '=' * 80 + '\n\n')

                # Виводимо детальну інформацію
                for reason, entries in sorted(reasons.items(), key=lambda x: len(x[1]), reverse=True):
                    f.write(f'\n{"=" * 80}\n')
                    f.write(f'ПРИЧИНА: {reason} ({len(entries)} файлів)\n')
                    f.write(f'{"=" * 80}\n\n')
                    
                    for entry in entries:
                        f.write(f'FILE: {entry["file"]}\n')
                        if 'data' in entry:
                            f.write(f'DATA: {json.dumps(entry["data"], ensure_ascii=False)}\n')
                        f.write('\n')

            self.stdout.write(self.style.WARNING(
                f'📝 Пропущені файли збережено в: {skip_log_file}'
            ))

    def parse_fp3_file(self, fp3_path):
        """Парсинг .fp3 файлу (FastReport XML)"""
        try:
            tree = ET.parse(fp3_path)
            root = tree.getroot()

            data = {
                'filename': fp3_path.name,
                'license_plate': None,
                'model': None,
                'chassis': None,
                'full_vin': None,
                'mileage': None,
                'date': None,
                'date_obj': None,
                'invoice_number': None,
                'client_name': None,
                'client_phone': None,
                'works': [],
                'parts': []
            }

            # Витягуємо дані з XML
            for elem in root.iter():
                if elem.tag == 'u' and 'v' in elem.attrib:
                    value = elem.attrib['v']
                    
                    # Держномер (8-10 символів, містить букви та цифри)
                    if re.match(r'^[A-ZА-ЯІЇЄ]{2}\d{4}[A-ZА-ЯІЇЄ]{2}$', value):
                        data['license_plate'] = value
                    
                    # Модель (починається з "Iveco")
                    elif value.startswith('Iveco'):
                        data['model'] = value
                    
                    # Шасі (7 цифр)
                    elif re.match(r'^\d{7}$', value):
                        data['chassis'] = value
                        # Генеруємо неповний VIN
                        data['full_vin'] = f'XXXXXXXX{value}'
                    
                    # Повний VIN (17 символів)
                    elif re.match(r'^[A-Z0-9]{17}$', value):
                        data['full_vin'] = value
                        if not data['chassis']:
                            data['chassis'] = value[-7:]
                    
                    # Пробіг (число більше 1000, менше 2000000)
                    elif value.isdigit() and 1000 < int(value) < 2000000:
                        if not data['mileage'] or int(value) > data['mileage']:
                            data['mileage'] = int(value)
                    
                    # Дата (формат ДДММРР)
                    elif re.match(r'^\d{6}$', value):
                        data['date'] = value
                        data['date_obj'] = self.parse_date_ddmmyy(value)
                    
                    # Номер рахунку (4-5 цифр на початку)
                    elif re.match(r'^\d{4,5}$', value) and not data['invoice_number']:
                        data['invoice_number'] = value
                    
                    # Ім'я клієнта (містить букви, довше 3 символів)
                    elif len(value) > 3 and re.search(r'[а-яіїєА-ЯІЇЄa-zA-Z]', value):
                        if not data['client_name']:
                            data['client_name'] = value
                    
                    # Телефон (починається з 0 або +380)
                    elif re.match(r'^(\+380|380|0|8)\d{9}', value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
                        normalized_phone = self.normalize_phone_number(value)
                        if normalized_phone:
                            data['client_phone'] = normalized_phone

            return data if data['license_plate'] else None

        except Exception as e:
            return None

    def parse_date_ddmmyy(self, date_str):
        """Парсинг дати формату ДДММРР"""
        try:
            day = int(date_str[0:2])
            month = int(date_str[2:4])
            year = int(date_str[4:6])
            
            # Визначаємо століття (якщо рік < 50, то 2000+, інакше 1900+)
            if year < 50:
                year += 2000
            else:
                year += 1900
            
            return datetime(year, month, day)
        except:
            return datetime.now()

    def normalize_phone_number(self, phone):
        """
        Нормалізація номера телефону до формату +380XXXXXXXXX
        
        Приклади:
            067... -> +38067...
            0671234567 -> +380671234567
            380671234567 -> +380671234567
            +380671234567 -> +380671234567
            (067) 123-45-67 -> +380671234567
        """
        if not phone:
            return ''
        
        # Прибираємо всі нецифрові символи окрім +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Якщо номер починається з +380
        if cleaned.startswith('+380'):
            if len(cleaned) == 13:  # +380XXXXXXXXX
                return cleaned
            else:
                return ''  # Невірна довжина
        
        # Якщо номер починається з 380
        if cleaned.startswith('380'):
            if len(cleaned) == 12:  # 380XXXXXXXXX
                return '+' + cleaned
            else:
                return ''
        
        # Якщо номер починається з 0
        if cleaned.startswith('0'):
            if len(cleaned) == 10:  # 0XXXXXXXXX
                return '+38' + cleaned
            else:
                return ''
        
        # Якщо номер починається з 8 (старий формат)
        if cleaned.startswith('8') and len(cleaned) == 10:
            return '+38' + cleaned[1:]  # Замінюємо 8 на +38
        
        # Інші випадки - повертаємо порожній рядок
        return ''

    def print_extracted_data(self, data):
        """Вивід витягнутих даних"""
        self.stdout.write('\n📄 Витягнуті дані:')
        self.stdout.write(f"  Держномер: {data['license_plate']}")
        self.stdout.write(f"  Модель: {data['model']}")
        self.stdout.write(f"  Шасі: {data['chassis']}")
        self.stdout.write(f"  VIN: {data['full_vin']}")
        self.stdout.write(f"  Пробіг: {data['mileage']} км")
        self.stdout.write(f"  Дата: {data['date']}")
        self.stdout.write(f"  Рахунок: {data['invoice_number']}")
        self.stdout.write(f"  Клієнт: {data['client_name']}")
        self.stdout.write(f"  Телефон: {data['client_phone']}")

    @transaction.atomic
    def import_to_database(self, data):
        """Імпорт даних у базу даних"""
        created_counts = {
            'clients': 0,
            'trucks': 0,
            'orders': 0,
            'works': 0,
            'parts': 0
        }

        # 1. Клієнт
        client, client_created = self.get_or_create_client(data)
        if client_created:
            created_counts['clients'] += 1
        if self.verbose:
            self.stdout.write(f"  👤 Клієнт: {client.name} (ID: {client.id})")

        # 2. Вантажівка
        truck, truck_created = self.get_or_create_truck(data, client)
        if truck_created:
            created_counts['trucks'] += 1
        if self.verbose:
            self.stdout.write(f"  🚛 Вантажівка: {truck.license_plate} (ID: {truck.id})")

        # 3. Сервісний наряд
        order, order_created = self.create_service_order(data, client, truck)
        if order_created:
            created_counts['orders'] += 1
        if self.verbose:
            self.stdout.write(f"  📋 Наряд: #{order.order_number} (ID: {order.id})")

        return created_counts

    def get_or_create_client(self, data):
        """Створення або пошук клієнта"""
        client_name = data.get('client_name', 'Клієнт не вказаний')
        client_phone = data.get('client_phone', '')
        
        # Нормалізуємо телефон
        normalized_phone = self.normalize_phone_number(client_phone)

        # Пошук по телефону
        if normalized_phone:
            # Шукаємо по нормалізованому телефону
            client = Client.objects.filter(phone=normalized_phone).first()
            if client:
                return client, False
            
            # Шукаємо по оригінальному (якщо в базі старий формат)
            if client_phone != normalized_phone:
                client = Client.objects.filter(phone=client_phone).first()
                if client:
                    # Оновлюємо телефон на нормалізований
                    client.phone = normalized_phone
                    client.save()
                    if self.verbose:
                        self.stdout.write(self.style.SUCCESS(
                            f'    🔄 Оновлено телефон клієнта: {client_phone} -> {normalized_phone}'
                        ))
                    return client, False

        # Пошук по імені
        client = Client.objects.filter(name__iexact=client_name).first()
        if client:
            # Якщо знайшли по імені, але телефону немає - додаємо
            if normalized_phone and not client.phone:
                client.phone = normalized_phone
                client.save()
                if self.verbose:
                    self.stdout.write(self.style.SUCCESS(
                        f'    📞 Додано телефон клієнту: {normalized_phone}'
                    ))
            return client, False

        # Створюємо нового
        client = Client.objects.create(
            name=client_name,
            phone=normalized_phone,  # Використовуємо нормалізований
            email='',
            notes=f'Автоматично створено при імпорті з fp3: {data["filename"]}'
        )
        
        if self.verbose:
            phone_display = f' ({normalized_phone})' if normalized_phone else ''
            self.stdout.write(self.style.SUCCESS(
                f'    ✨ Створено нового клієнта: {client_name}{phone_display}'
            ))
        
        return client, True

    def get_or_create_truck(self, data, client):
        """Створення або пошук вантажівки"""
        license_plate = data['license_plate']
        
        # Шукаємо вантажівку
        truck = Truck.objects.filter(license_plate=license_plate).first()

        if truck:
            # Оновлюємо пробіг
            if data.get('mileage') and data['mileage'] > (truck.mileage or 0):
                truck.mileage = data['mileage']
                truck.save()
            return truck, False

        # Генеруємо VIN
        full_vin = data.get('full_vin')
        if not full_vin:
            # Немає ні шасі, ні VIN - генеруємо TEMP
            chassis_digits = re.sub(r'\D', '', license_plate)[-4:]
            full_vin = f'TEMP0000{chassis_digits.zfill(8)}'

        # Модель
        model_name = data.get('model')
        if not model_name or model_name.strip() == '':
            model_name = 'Не визначено'
        
        base_model, _ = IvecoBaseModel.objects.get_or_create(name=model_name)

        # Створюємо вантажівку
        truck = Truck.objects.create(
            owner=client,
            license_plate=license_plate,
            base_model=base_model,
            full_vin=full_vin,
            mileage=data.get('mileage'),
            notes=f'Автоматично створено при імпорті з fp3: {data["filename"]}'
        )

        if self.verbose:
            if full_vin.startswith('XXXXXXXX') or full_vin.startswith('TEMP'):
                self.stdout.write(self.style.WARNING(
                    f'    ⚠️  Створено вантажівку з неповним VIN: {license_plate} ({full_vin})'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'    ✨ Створено нову вантажівку: {license_plate}'
                ))

        return truck, True

    def create_service_order(self, data, client, truck):
        """Створення сервісного наряду"""
        invoice_number = data.get('invoice_number', 'FP3-UNKNOWN')
        
        # Перевіряємо чи не існує
        existing_order = ServiceOrder.objects.filter(
            invoice_number=invoice_number
        ).first()

        if existing_order:
            if self.verbose:
                self.stdout.write(self.style.WARNING(
                    f'    ⚠️  Наряд #{invoice_number} вже існує (ID: {existing_order.id})'
                ))
            return existing_order, False

        # Створюємо наряд
        order = ServiceOrder.objects.create(
            client=client,
            truck=truck,
            order_number=f'FP3-{invoice_number}',
            invoice_number=invoice_number,
            status='CLOSED',
            description=f'Імпортовано з fp3: {data["filename"]}',
            mileage_at_service=data.get('mileage')
        )

        # Встановлюємо дату
        if data.get('date_obj'):
            aware_datetime = make_aware(data['date_obj'])
            order.created_at = aware_datetime
            order.save()

        return order, True

    def print_summary(self, stats, dry_run, error_log_file, skip_log_file):
        """Вивід підсумкової статистики"""
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('📊 СТАТИСТИКА ІМПОРТУ')
        self.stdout.write('=' * 80)
        self.stdout.write(f"Оброблено файлів: {stats['total']}")
        self.stdout.write(self.style.SUCCESS(f"✅ Успішно: {stats['success']}"))
        
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(
                f"❌ Помилок: {stats['errors']} (дивіться {error_log_file})"
            ))
        
        if stats['skipped'] > 0:
            self.stdout.write(self.style.WARNING(
                f"⚠️  Пропущено: {stats['skipped']} (дивіться {skip_log_file})"
            ))

        if not dry_run and stats['success'] > 0:
            self.stdout.write('\n📈 Створено в БД:')
            self.stdout.write(f"  👤 Клієнтів: {stats['created']['clients']}")
            self.stdout.write(f"  🚗 Вантажівок: {stats['created']['trucks']}")
            self.stdout.write(f"  📋 Нарядів: {stats['created']['orders']}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  ТЕСТОВИЙ РЕЖИМ - Дані НЕ збережено в базу даних'
            ))
        
        self.stdout.write('=' * 80)
        
        # Підказки
        if stats['errors'] > 0:
            self.stdout.write(self.style.WARNING(
                f'\n💡 Для повторного імпорту файлів з помилками використайте:'
            ))
            self.stdout.write(
                f'   python manage.py import_fp3_to_crm <папка> --retry-errors --error-log {error_log_file}'
            )
        
        self.stdout.write('\n')