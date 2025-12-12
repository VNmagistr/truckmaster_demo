"""
Django management command для імпорту рахунків з PDF файлів у CRM систему.

Функціонал:
- Парсинг PDF файлів з рахунками
- Витягування даних: номер рахунку, дата, клієнт, вантажівка, роботи, запчастини
- Автоматичне створення/пошук клієнтів
- Автоматичне створення/пошук вантажівок
- Створення ServiceOrder зі статусом CLOSED
- Додавання робіт та запчастин

Використання:
    python manage.py import_pdf_invoices <path_to_pdf_folder> [--dry-run]

Приклади:
    python manage.py import_pdf_invoices /home/ubuntu/pdf_invoices --dry-run
    python manage.py import_pdf_invoices /home/ubuntu/pdf_invoices
"""

import os
import re
from decimal import Decimal
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import make_aware

# PDF парсинг
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

from clients.models import Client, Truck, IvecoBaseModel
from orders.models import ServiceOrder, WorkPrice, WorkGroup, Part


class Command(BaseCommand):
    help = 'Імпортує рахунки з PDF файлів у CRM систему'

    def add_arguments(self, parser):
        parser.add_argument(
            'pdf_folder',
            type=str,
            help='Шлях до папки з PDF файлами'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Тестовий запуск без збереження в базу даних'
        )

    def handle(self, *args, **options):
        if PyPDF2 is None:
            self.stdout.write(self.style.ERROR(
                'PyPDF2 не встановлено! Встановіть: pip install PyPDF2'
            ))
            return

        pdf_folder = options['pdf_folder']
        dry_run = options['dry_run']

        if not os.path.exists(pdf_folder):
            self.stdout.write(self.style.ERROR(f'Папка не існує: {pdf_folder}'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('=' * 80))
            self.stdout.write(self.style.WARNING('ТЕСТОВИЙ РЕЖИМ (--dry-run)'))
            self.stdout.write(self.style.WARNING('Дані НЕ будуть збережені в базу даних'))
            self.stdout.write(self.style.WARNING('=' * 80))

        # Знаходимо всі PDF файли
        pdf_files = list(Path(pdf_folder).glob('*.pdf'))
        
        if not pdf_files:
            self.stdout.write(self.style.WARNING(f'PDF файли не знайдено в {pdf_folder}'))
            return

        self.stdout.write(f'\nЗнайдено PDF файлів: {len(pdf_files)}\n')

        # Статистика
        stats = {
            'total': len(pdf_files),
            'success': 0,
            'errors': 0,
            'skipped': 0
        }

        # Обробка кожного файлу
        for pdf_file in pdf_files:
            self.stdout.write(f'\n{"=" * 80}')
            self.stdout.write(f'Обробка: {pdf_file.name}')
            self.stdout.write(f'{"=" * 80}')

            try:
                # Парсимо PDF
                data = self.parse_pdf(pdf_file)
                
                if not data:
                    self.stdout.write(self.style.WARNING('⚠️  Файл пропущено (не вдалося витягти дані)'))
                    stats['skipped'] += 1
                    continue

                # Виводимо витягнуті дані
                self.print_extracted_data(data)

                if not dry_run:
                    # Імпортуємо в базу даних
                    self.import_to_database(data)
                    self.stdout.write(self.style.SUCCESS('✅ Успішно імпортовано'))
                else:
                    self.stdout.write(self.style.WARNING('🔍 Тестовий режим - дані НЕ збережено'))

                stats['success'] += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Помилка: {str(e)}'))
                stats['errors'] += 1
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))

        # Підсумкова статистика
        self.print_summary(stats, dry_run)

    def parse_pdf(self, pdf_path):
        """Парсинг PDF файлу та витягування даних"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Витягуємо текст з першої сторінки
                if len(reader.pages) == 0:
                    return None
                    
                text = reader.pages[0].extract_text()
                
                if not text:
                    return None

                # Парсимо дані
                data = self.extract_data_from_text(text)
                data['filename'] = pdf_path.name
                
                return data

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Помилка читання PDF: {str(e)}'))
            return None

    def extract_data_from_text(self, text):
        """Витягування даних з тексту PDF"""
        data = {
            'invoice_number': None,
            'date': None,
            'date_obj': None,
            'client_name': None,
            'license_plate': None,
            'model': None,
            'chassis': None,
            'full_vin': None,
            'mileage': None,
            'works': [],
            'parts': []
        }

        lines = text.split('\n')

        # Витягуємо номер рахунку
        for line in lines:
            # Рахунок на оплату № 10836 від 08 січня 2025 р.
            match = re.search(r'Рахунок на оплату\s*№\s*(\d+)\s+від\s+(.+?)\s+р\.', line)
            if match:
                data['invoice_number'] = match.group(1)
                date_str = match.group(2).strip()
                data['date'] = date_str
                data['date_obj'] = self.parse_ukrainian_date(date_str)
                break

        # Витягуємо покупця
        for i, line in enumerate(lines):
            if 'Покупець:' in line:
                # Наступний рядок містить назву покупця
                if i + 1 < len(lines):
                    client_name = lines[i + 1].strip()
                    # Прибираємо "ТОВАРИСТВО З ОБМЕЖЕНОЮ ВІДПОВІДАЛЬНІСТЮ" та подібне
                    client_name = re.sub(r'^(ТОВАРИСТВО З ОБМЕЖЕНОЮ ВІДПОВІДАЛЬНІСТЮ|ТОВ|ФОП|ПП)\s*["\']?', '', client_name, flags=re.IGNORECASE)
                    client_name = client_name.strip('"\'')
                    data['client_name'] = client_name
                break

        # Витягуємо дані вантажівки: Модель, Держ. №, Шасі, Пробіг
        for line in lines:
            # Модель: Iveco Daily 70C16 Держ. №: ВС6900ММ Шасі: ZCFCA70B405421963 Пробіг: 449 904
            if 'Модель:' in line:
                # Модель
                model_match = re.search(r'Модель:\s*(.+?)\s+Держ', line)
                if model_match:
                    data['model'] = model_match.group(1).strip()

                # Держномер
                plate_match = re.search(r'Держ\.\s*№:\s*([A-ZА-ЯІЇЄ0-9]+)', line, re.IGNORECASE)
                if plate_match:
                    data['license_plate'] = plate_match.group(1).strip()

                # Шасі (VIN)
                chassis_match = re.search(r'Шасі:\s*([A-Z0-9]+)', line)
                if chassis_match:
                    chassis = chassis_match.group(1).strip()
                    data['chassis'] = chassis
                    data['full_vin'] = chassis  # В PDF зазвичай повний VIN

                # Пробіг
                mileage_match = re.search(r'Пробіг:\s*([\d\s]+)', line)
                if mileage_match:
                    mileage_str = mileage_match.group(1).replace(' ', '')
                    try:
                        data['mileage'] = int(mileage_str)
                    except ValueError:
                        pass
                break

        # Витягуємо таблицю з роботами та запчастинами
        in_table = False
        for line in lines:
            # Початок таблиці
            if re.match(r'^№\s+Повна назва товару', line):
                in_table = True
                continue

            # Кінець таблиці
            if 'Разом без ПДВ:' in line or 'Всього з ПДВ:' in line:
                in_table = False
                break

            if in_table and line.strip():
                # Парсимо рядок таблиці
                # Формат: № Назва Од.вим. К-ть Ціна Сума
                item = self.parse_table_row(line)
                if item:
                    # Визначаємо чи це робота чи запчастина
                    if item['unit'] == 'год' or 'заміна' in item['name'].lower():
                        data['works'].append(item)
                    else:
                        data['parts'].append(item)

        return data

    def parse_table_row(self, line):
        """Парсинг рядка таблиці"""
        try:
            # Видаляємо номер на початку (1, 2, 3...)
            line = re.sub(r'^\d+\s+', '', line)
            
            parts = line.split()
            if len(parts) < 4:
                return None

            # Останні 3 значення: кількість, ціна, сума
            try:
                quantity = parts[-3].replace(',', '.')
                price = parts[-2].replace(',', '.')
                total = parts[-1].replace(',', '.')
                
                quantity = Decimal(quantity)
                price = Decimal(price)
                total = Decimal(total)
            except (ValueError, IndexError):
                return None

            # Одиниця виміру перед кількістю
            unit = parts[-4] if len(parts) > 4 else 'шт'

            # Назва - все що залишилось
            name = ' '.join(parts[:-4]) if len(parts) > 4 else ' '.join(parts[:-3])

            return {
                'name': name.strip(),
                'unit': unit,
                'quantity': quantity,
                'price': price,
                'total': total
            }
        except Exception as e:
            return None

    def parse_ukrainian_date(self, date_str):
        """Парсинг української дати: '08 січня 2025'"""
        months = {
            'січня': 1, 'січ': 1,
            'лютого': 2, 'лют': 2,
            'березня': 3, 'бер': 3,
            'квітня': 4, 'квіт': 4,
            'травня': 5, 'трав': 5,
            'червня': 6, 'черв': 6,
            'липня': 7, 'лип': 7,
            'серпня': 8, 'серп': 8,
            'вересня': 9, 'вер': 9,
            'жовтня': 10, 'жовт': 10,
            'листопада': 11, 'лист': 11,
            'грудня': 12, 'груд': 12
        }

        # Шукаємо паттерн: число місяць рік
        match = re.search(r'(\d{1,2})\s+([а-яіїє]+)\s+(\d{4})', date_str, re.IGNORECASE)
        if match:
            day = int(match.group(1))
            month_name = match.group(2).lower()
            year = int(match.group(3))

            month = months.get(month_name)
            if month:
                return datetime(year, month, day)

        return datetime.now()

    def normalize_phone_number(self, phone):
        """
        Нормалізація українського номера телефону до формату +380XXXXXXXXX
        
        Приклади:
            067123456 -> +380671234567
            0671234567 -> +380671234567
            380671234567 -> +380671234567
            +380671234567 -> +380671234567
            (067) 123-45-67 -> +380671234567
        """
        if not phone:
            return ''
        
        # Прибираємо всі символи крім цифр і +
        phone = re.sub(r'[^\d+]', '', phone)
        
        # Прибираємо + на початку для обробки
        phone = phone.lstrip('+')
        
        # Різні варіанти форматів
        if phone.startswith('380'):
            # Вже в міжнародному форматі: 380671234567
            if len(phone) == 12:
                return f'+{phone}'
        elif phone.startswith('0'):
            # Національний формат: 0671234567
            if len(phone) == 10:
                return f'+38{phone}'
        elif len(phone) == 9:
            # Без нуля на початку: 671234567
            return f'+380{phone}'
        
        # Якщо не вдалось розпізнати - повертаємо оригінал
        return phone if phone else ''

    def print_extracted_data(self, data):
        """Вивід витягнутих даних"""
        self.stdout.write('\n📄 Витягнуті дані:')
        self.stdout.write(f"  Номер рахунку: {data['invoice_number']}")
        self.stdout.write(f"  Дата: {data['date']}")
        self.stdout.write(f"  Клієнт: {data['client_name']}")
        self.stdout.write(f"  Держномер: {data['license_plate']}")
        self.stdout.write(f"  Модель: {data['model']}")
        self.stdout.write(f"  VIN/Шасі: {data['full_vin']}")
        self.stdout.write(f"  Пробіг: {data['mileage']} км")
        self.stdout.write(f"  Робіт: {len(data['works'])}")
        self.stdout.write(f"  Запчастин: {len(data['parts'])}")

    @transaction.atomic
    def import_to_database(self, data):
        """Імпорт даних у базу даних"""
        # 1. Створюємо/знаходимо клієнта
        client = self.get_or_create_client(data)
        self.stdout.write(f"  👤 Клієнт: {client.name} (ID: {client.id})")

        # 2. Створюємо/знаходимо вантажівку
        truck = self.get_or_create_truck(data, client)
        self.stdout.write(f"  🚛 Вантажівка: {truck.license_plate} (ID: {truck.id})")

        # 3. Створюємо сервісний наряд
        order = self.create_service_order(data, client, truck)
        self.stdout.write(f"  📋 Наряд: #{order.order_number} (ID: {order.id})")

        # 4. Додаємо роботи
        if data['works']:
            self.add_works_to_order(order, data['works'])
            self.stdout.write(f"  🔧 Додано робіт: {len(data['works'])}")

        # 5. Додаємо запчастини
        if data['parts']:
            self.add_parts_to_order(order, data['parts'])
            self.stdout.write(f"  🔩 Додано запчастин: {len(data['parts'])}")

    def get_or_create_client(self, data):
        """Створення або пошук клієнта"""
        client_name = data.get('client_name')
        
        if not client_name:
            client_name = 'Клієнт не вказаний'

        # Пошук по імені
        client = Client.objects.filter(name__iexact=client_name).first()
        
        if not client:
            # Створюємо нового клієнта
            client = Client.objects.create(
                name=client_name,
                email='',
                phone='',
                notes=f'Автоматично створено при імпорті з PDF рахунку #{data["invoice_number"]}'
            )
            self.stdout.write(self.style.SUCCESS(f'    ✨ Створено нового клієнта: {client_name}'))
        
        return client

    def get_or_create_truck(self, data, client):
        """Створення або пошук вантажівки"""
        license_plate = data.get('license_plate')
        
        if not license_plate:
            raise ValueError('Держномер не знайдено в PDF')

        # Нормалізуємо держномер
        license_plate = license_plate.upper().replace(' ', '')

        # Шукаємо вантажівку
        truck = Truck.objects.filter(license_plate=license_plate).first()

        if truck:
            # Оновлюємо пробіг якщо новий більший
            if data.get('mileage') and data['mileage'] > (truck.mileage or 0):
                truck.mileage = data['mileage']
                truck.save()
            return truck

        # Створюємо нову вантажівку
        full_vin = data.get('full_vin', '')
        
        # Перевіряємо довжину VIN
        if len(full_vin) != 17:
            self.stdout.write(self.style.WARNING(
                f'    ⚠️  VIN неповний ({len(full_vin)} символів): {full_vin}'
            ))

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
            full_vin=full_vin or f'TEMP{license_plate}',
            mileage=data.get('mileage'),
            notes=f'Автоматично створено при імпорті з PDF рахунку #{data["invoice_number"]}'
        )

        self.stdout.write(self.style.SUCCESS(
            f'    ✨ Створено нову вантажівку: {license_plate}'
        ))

        return truck

    def create_service_order(self, data, client, truck):
        """Створення сервісного наряду"""
        invoice_number = data.get('invoice_number', 'PDF-IMPORT')
        
        # Перевіряємо чи не існує вже такий наряд
        existing_order = ServiceOrder.objects.filter(
            invoice_number=invoice_number
        ).first()

        if existing_order:
            self.stdout.write(self.style.WARNING(
                f'    ⚠️  Наряд #{invoice_number} вже існує (ID: {existing_order.id})'
            ))
            return existing_order

        # Створюємо наряд
        order = ServiceOrder.objects.create(
            client=client,
            truck=truck,
            order_number=f'PDF-{invoice_number}',
            invoice_number=invoice_number,
            status='CLOSED',
            description=f'Імпортовано з PDF: {data["filename"]}',
            mileage_at_service=data.get('mileage')
        )

        # Встановлюємо дату створення
        if data.get('date_obj'):
            aware_datetime = make_aware(data['date_obj'])
            order.created_at = aware_datetime
            order.save()

        return order

    def add_works_to_order(self, order, works):
        """Додавання робіт до наряду"""
        # Отримуємо або створюємо робочу групу
        work_group, _ = WorkGroup.objects.get_or_create(
            name='Імпортовані з PDF'
        )

        for work_data in works:
            work_name = work_data['name']
            hours = work_data['quantity']

            # Шукаємо роботу
            work_price, created = WorkPrice.objects.get_or_create(
                work_group=work_group,
                name=work_name,
                defaults={'standard_hours': hours}
            )

            if created:
                self.stdout.write(f'      ✨ Створено роботу: {work_name}')

            # Додаємо до наряду
            order.works.add(work_price)

    def add_parts_to_order(self, order, parts):
        """Додавання запчастин до наряду"""
        for part_data in parts:
            part_name = part_data['name']
            quantity = part_data['quantity']
            price = part_data['price']

            # Шукаємо запчастину по назві
            part = Part.objects.filter(name__iexact=part_name).first()

            if not part:
                # Створюємо нову запчастину
                # Генеруємо SKU
                last_part = Part.objects.order_by('-id').first()
                next_id = (last_part.id + 1) if last_part else 1
                sku = f'PDF-{next_id:05d}'

                part = Part.objects.create(
                    sku=sku,
                    name=part_name,
                    unit_price=price,
                    stock_quantity=0,
                    notes='Автоматично створено при імпорті з PDF'
                )
                self.stdout.write(f'      ✨ Створено запчастину: {part_name} (SKU: {sku})')

            # Додаємо до наряду
            order.parts.add(part)

    def print_summary(self, stats, dry_run):
        """Вивід підсумкової статистики"""
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('📊 ПІДСУМКОВА СТАТИСТИКА')
        self.stdout.write('=' * 80)
        self.stdout.write(f"Оброблено файлів: {stats['total']}")
        self.stdout.write(self.style.SUCCESS(f"✅ Успішно: {stats['success']}"))
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"❌ Помилок: {stats['errors']}"))
        if stats['skipped'] > 0:
            self.stdout.write(self.style.WARNING(f"⚠️  Пропущено: {stats['skipped']}"))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  ТЕСТОВИЙ РЕЖИМ - Дані НЕ збережено в базу даних'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Імпорт завершено'))
        
        self.stdout.write('=' * 80 + '\n')