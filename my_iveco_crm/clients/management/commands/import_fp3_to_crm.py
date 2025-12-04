# clients/management/commands/import_fp3_to_crm.py

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from decimal import Decimal
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.timezone import make_aware

from clients.models import Client, Truck, IvecoBaseModel
from orders.models import ServiceOrder, WorkGroup, WorkPrice, ServiceWork
from inventory.models import Part, UsedPart


class Command(BaseCommand):
    help = 'Імпортує дані з .fp3 файлів у CRM систему'

    def add_arguments(self, parser):
        parser.add_argument(
            'folder_path',
            type=str,
            help='Шлях до папки з .fp3 файлами'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Тестовий режим (без збереження в БД)'
        )

    def handle(self, *args, **options):
        folder_path = options['folder_path']
        dry_run = options.get('dry_run', False)

        if not os.path.exists(folder_path):
            self.stdout.write(self.style.ERROR(f'Папка не знайдена: {folder_path}'))
            return

        # Знаходимо всі .fp3 файли
        fp3_files = list(Path(folder_path).glob('*.fp3'))
        
        if not fp3_files:
            self.stdout.write(self.style.WARNING('Не знайдено .fp3 файлів у папці'))
            return

        self.stdout.write(self.style.SUCCESS(f'\n{"="*80}'))
        self.stdout.write(self.style.SUCCESS(f'Знайдено {len(fp3_files)} файлів для імпорту'))
        if dry_run:
            self.stdout.write(self.style.WARNING('РЕЖИМ ТЕСТУВАННЯ - дані НЕ будуть збережені'))
        self.stdout.write(self.style.SUCCESS(f'{"="*80}\n'))

        stats = {
            'processed': 0,
            'success': 0,
            'errors': 0,
            'skipped': 0,
            'clients_created': 0,
            'trucks_created': 0,
            'orders_created': 0,
            'works_created': 0,
            'parts_created': 0
        }

        for file_path in fp3_files:
            self.stdout.write(f'\n📄 Обробка: {file_path.name}')
            stats['processed'] += 1

            try:
                # Парсимо файл
                data = self.parse_fp3_file(file_path)
                
                if not data:
                    self.stdout.write(self.style.WARNING('  ⚠️  Не вдалося розпарсити файл'))
                    stats['skipped'] += 1
                    continue

                # Валідація обов'язкових полів
                if not data.get('plate'):
                    self.stdout.write(self.style.WARNING('  ⚠️  Не знайдено держномер'))
                    stats['skipped'] += 1
                    continue

                if not data.get('invoice'):
                    self.stdout.write(self.style.WARNING('  ⚠️  Не знайдено номер рахунку'))
                    stats['skipped'] += 1
                    continue

                # Імпортуємо в БД
                if not dry_run:
                    result = self.import_to_database(data)
                    if result:
                        stats['success'] += 1
                        for key in ['clients_created', 'trucks_created', 'orders_created', 
                                   'works_created', 'parts_created']:
                            stats[key] += result.get(key, 0)
                        self.stdout.write(self.style.SUCCESS('  ✅ Успішно імпортовано'))
                    else:
                        stats['errors'] += 1
                else:
                    # Dry run - тільки показуємо що буде імпортовано
                    self.display_import_preview(data)
                    stats['success'] += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Помилка: {e}'))
                stats['errors'] += 1

        # Виводимо статистику
        self.display_statistics(stats, dry_run)

    def parse_fp3_file(self, file_path):
        """Парсить .fp3 файл і витягує всі дані"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            data = {
                'plate': None,
                'chassis': None,
                'mileage': None,
                'date': None,
                'date_obj': None,
                'model': None,
                'invoice': None,
                'client_name': None,
                'client_phone': None,
                'works': [],
                'parts': []
            }
            
            page0 = root.find('.//page0')
            if not page0:
                return None
            
            # Витягуємо дані
            for elem in page0.iter():
                if 'u' not in elem.attrib:
                    continue
                
                text = elem.attrib['u']
                
                # Номер рахунку
                if 'Рахунок-фактура №' in text:
                    invoice_match = re.search(r'№\s*(\d+)', text)
                    if invoice_match:
                        data['invoice'] = invoice_match.group(1)
                
                # Дата
                if 'від' in text and 'р.' in text:
                    date_str = text.replace('від ', '').replace(' р.', '').strip()
                    data['date'] = date_str
                    data['date_obj'] = self.parse_date(date_str)
                
                # Модель (формат 70С17)
                if re.match(r'^\d{2}[А-Я]\d{2}$', text):
                    if not data['model']:
                        data['model'] = text
                
                # Держномер (формат АС9744СК)
                if re.match(r'^[А-Я]{2}\d{4}[А-Я]{2}$', text):
                    data['plate'] = text
                
                # Шасі (7 цифр)
                if len(text) == 7 and text.isdigit():
                    if not data['chassis']:
                        data['chassis'] = text
                
                # Пробіг
                mileage_match = re.match(r'^(\d{1,3})\s*(\d{3})$', text)
                if mileage_match:
                    data['mileage'] = mileage_match.group(1) + mileage_match.group(2)
                
                # Клієнт (ім'я та телефон)
                if re.search(r'\d{10}', text):  # Містить телефон
                    lines = text.split('\n')
                    if len(lines) >= 2:
                        data['client_name'] = lines[0].strip()
                        phone_match = re.search(r'(\+?\d{10,13})', lines[1])
                        if phone_match:
                            data['client_phone'] = phone_match.group(1)
            
            # Збираємо роботи та запчастини з Band1 (основний список)
            self.extract_works_and_parts(page0, data)
            
            return data
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Помилка парсингу: {e}'))
            return None

    def extract_works_and_parts(self, page0, data):
        """Витягує роботи та запчастини з XML"""
        # Шукаємо всі блоки <b1> - це рядки таблиці
        for band in page0.findall('.//b1'):
            item_name = None
            unit = None
            quantity = None
            price = None
            
            for elem in band:
                if elem.tag == 'm1' and 'u' in elem.attrib:
                    item_name = elem.attrib['u']
                elif elem.tag == 'm2' and 'u' in elem.attrib:
                    unit = elem.attrib['u']
                elif elem.tag == 'm3' and 'u' in elem.attrib:
                    quantity = elem.attrib['u'].replace(',', '.')
                elif elem.tag == 'm5' and 'u' in elem.attrib:
                    price = elem.attrib['u'].replace(',', '.')
            
            if item_name and unit and quantity:
                item_data = {
                    'name': item_name,
                    'unit': unit,
                    'quantity': quantity,
                    'price': price
                }
                
                # Розділяємо на роботи та запчастини
                if unit in ['годин', 'год', 'год.']:
                    data['works'].append(item_data)
                else:
                    data['parts'].append(item_data)

    def parse_date(self, date_str):
        """Конвертує українську дату в datetime"""
        months = {
            'січня': 1, 'лютого': 2, 'березня': 3, 'квітня': 4,
            'травня': 5, 'червня': 6, 'липня': 7, 'серпня': 8,
            'вересня': 9, 'жовтня': 10, 'листопада': 11, 'грудня': 12
        }
        
        try:
            parts = date_str.split()
            day = int(parts[0])
            month = months.get(parts[1], 1)
            year = int(parts[2])
            return datetime(year, month, day)
        except:
            return timezone.now()

    def import_to_database(self, data):
        """Імпортує дані в базу даних"""
        result = {
            'clients_created': 0,
            'trucks_created': 0,
            'orders_created': 0,
            'works_created': 0,
            'parts_created': 0
        }
        
        try:
            with transaction.atomic():
                # 1. Створюємо або знаходимо клієнта
                client = self.get_or_create_client(data)
                if client and hasattr(client, '_created'):
                    result['clients_created'] = 1
                    self.stdout.write(f'  👤 Створено клієнта: {client.name}')
                elif client:
                    self.stdout.write(f'  👤 Клієнт: {client.name}')
                
                if not client:
                    self.stdout.write(self.style.WARNING('  ⚠️  Не вдалося створити клієнта'))
                    return None
                
                # 2. Створюємо або знаходимо вантажівку
                truck, truck_created = self.get_or_create_truck(data, client)
                if truck_created:
                    result['trucks_created'] = 1
                    self.stdout.write(f'  🚗 Створено вантажівку: {truck.license_plate}')
                    if not data.get('chassis') or len(data.get('chassis', '')) < 17:
                        self.stdout.write(self.style.WARNING(
                            f'  ⚠️  УВАГА: Неповний VIN! Потрібно доповнити вручну'
                        ))
                else:
                    self.stdout.write(f'  🚗 Вантажівка: {truck.license_plate}')
                
                # 3. Створюємо замовлення-наряд
                order = self.create_service_order(data, client, truck)
                if order:
                    result['orders_created'] = 1
                    self.stdout.write(f'  📋 Створено наряд: №{order.order_number}')
                
                # 4. Додаємо роботи
                works_added = self.add_works_to_order(data, order)
                result['works_created'] = works_added
                if works_added > 0:
                    self.stdout.write(f'  🔧 Додано робіт: {works_added}')
                
                # 5. Додаємо запчастини
                parts_added = self.add_parts_to_order(data, order)
                result['parts_created'] = parts_added
                if parts_added > 0:
                    self.stdout.write(f'  🛠  Додано запчастин: {parts_added}')
                
                return result
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Помилка імпорту в БД: {e}'))
            return None

    def get_or_create_client(self, data):
        """Створює або знаходить клієнта"""
        client_name = data.get('client_name')
        client_phone = data.get('client_phone')
        
        if not client_name:
            # Якщо немає імені, використовуємо номер авто як ідентифікатор
            client_name = f"Власник {data.get('plate', 'невідомо')}"
        
        # Шукаємо по телефону
        if client_phone:
            client = Client.objects.filter(phone__icontains=client_phone[-10:]).first()
            if client:
                return client
        
        # Шукаємо по імені
        client = Client.objects.filter(name__iexact=client_name).first()
        if client:
            return client
        
        # Створюємо нового
        client = Client.objects.create(
            name=client_name,
            phone=client_phone if client_phone else None
        )
        client._created = True
        return client

    def get_or_create_truck(self, data, client):
        """Створює або знаходить вантажівку"""
        plate = data.get('plate')
        
        # Шукаємо по держномеру
        truck = Truck.objects.filter(license_plate=plate).first()
        if truck:
            # Оновлюємо власника якщо змінився
            if truck.client != client:
                truck.client = client
                truck.save()
            return truck, False
        
        # Отримуємо або створюємо базову модель
        model_name = data.get('model')
        
        # Якщо модель не знайдена або порожня - використовуємо дефолтну
        if not model_name or model_name.strip() == '':
            model_name = 'Не визначено'
        
        base_model, _ = IvecoBaseModel.objects.get_or_create(
            name=model_name
        )
        
        # Створюємо VIN код
        chassis = data.get('chassis', '')
        if chassis and len(chassis) == 7:
            # Якщо тільки 7 цифр - додаємо префікс (неповний VIN)
            full_vin = f'XXXXXXXX{chassis}'  # Позначаємо що це неповний
        elif chassis and len(chassis) == 17:
            full_vin = chassis
        else:
            # Генеруємо тимчасовий VIN з номера
            plate_digits = re.sub(r'\D', '', plate)
            full_vin = f'TEMP000000{plate_digits:0>7}'
        
        # Створюємо вантажівку
        truck = Truck.objects.create(
            client=client,
            base_model=base_model,
            specific_model_name=model_name,
            full_vin=full_vin,
            license_plate=plate
        )
        
        return truck, True

    def create_service_order(self, data, client, truck):
        """Створює замовлення-наряд"""
        order_number = data.get('invoice')
        
        # Перевіряємо чи існує вже такий наряд
        existing_order = ServiceOrder.objects.filter(order_number=order_number).first()
        if existing_order:
            self.stdout.write(self.style.WARNING(
                f'  ⚠️  Наряд №{order_number} вже існує, пропускаємо'
            ))
            return None
        
        # Створюємо наряд
        order = ServiceOrder.objects.create(
            order_number=order_number,
            client=client,
            truck=truck,
            status='CLOSED',  # Старі наряди відразу закриті
            problem_description='Імпортовано з .fp3 файлу'
        )
        
        # Встановлюємо дату з файлу (робимо timezone-aware)
        if data.get('date_obj'):
            aware_datetime = make_aware(data['date_obj'])
            order.created_at = aware_datetime
            order.save(update_fields=['created_at'])
        
        return order

    def add_works_to_order(self, data, order):
        """Додає роботи до наряду"""
        if not order:
            return 0
        
        works_added = 0
        
        # Отримуємо або створюємо групу робіт
        work_group, _ = WorkGroup.objects.get_or_create(
            name='Імпортовані з fp3',
            defaults={'hourly_rate': Decimal('500.00')}
        )
        
        for work_data in data.get('works', []):
            work_name = work_data['name']
            hours = Decimal(work_data['quantity'])
            
            # Шукаємо роботу в прайсі
            work_price = WorkPrice.objects.filter(
                name__iexact=work_name
            ).first()
            
            # Якщо не знайдено - створюємо
            if not work_price:
                work_price = WorkPrice.objects.create(
                    work_group=work_group,
                    name=work_name,
                    standard_hours=hours
                    # price - це @property, не потрібно передавати
                )
            
            # Додаємо роботу до наряду
            ServiceWork.objects.create(
                service_order=order,
                work=work_price,
                hours_spent=hours,
                description=f'Імпортовано з fp3'
            )
            works_added += 1
        
        return works_added

    def add_parts_to_order(self, data, order):
        """Додає запчастини до наряду"""
        if not order:
            return 0
        
        parts_added = 0
        
        # Отримуємо перші роботи (прив'яжемо запчастини до них)
        service_works = order.works.all()
        if not service_works:
            # Якщо немає робіт, створюємо загальну
            work_group, _ = WorkGroup.objects.get_or_create(
                name='Імпортовані з fp3'
            )
            work_price, _ = WorkPrice.objects.get_or_create(
                work_group=work_group,
                name='Загальні запчастини',
                defaults={'standard_hours': Decimal('0')}
            )
            service_work = ServiceWork.objects.create(
                service_order=order,
                work=work_price,
                hours_spent=Decimal('0')
            )
            service_works = [service_work]
        
        service_work = service_works[0]
        
        for part_data in data.get('parts', []):
            part_name = part_data['name']
            quantity = int(float(part_data['quantity']))
            price_str = part_data.get('price', '0')
            
            try:
                price = Decimal(price_str)
            except:
                price = Decimal('0')
            
            # Шукаємо запчастину
            part = Part.objects.filter(name__iexact=part_name).first()
            
            # Якщо не знайдено - створюємо
            if not part:
                # Генеруємо SKU
                sku = f'FP3-{len(Part.objects.all()) + 1:05d}'
                
                part = Part.objects.create(
                    name=part_name,
                    sku_code=sku,
                    selling_price=price,
                    cost_price=Decimal('0'),
                    unit='шт' if part_data['unit'] == 'шт' else 'л'
                )
            
            # Додаємо до наряду
            UsedPart.objects.create(
                service_work=service_work,
                part=part,
                quantity=quantity
            )
            parts_added += 1
        
        # Оновлюємо загальну вартість наряду
        order.update_total_cost()
        
        return parts_added

    def display_import_preview(self, data):
        """Показує що буде імпортовано (dry-run режим)"""
        self.stdout.write(f'  📋 Наряд: №{data.get("invoice")}')
        self.stdout.write(f'  📅 Дата: {data.get("date")}')
        self.stdout.write(f'  👤 Клієнт: {data.get("client_name", "Н/Д")}')
        self.stdout.write(f'  📞 Телефон: {data.get("client_phone", "Н/Д")}')
        self.stdout.write(f'  🚗 Номер: {data.get("plate")}')
        self.stdout.write(f'  🔧 Модель: {data.get("model", "Н/Д")}')
        self.stdout.write(f'  🆔 Шасі: {data.get("chassis", "Н/Д")}')
        self.stdout.write(f'  📊 Пробіг: {data.get("mileage", "Н/Д")} км')
        self.stdout.write(f'  🔧 Робіт: {len(data.get("works", []))}')
        self.stdout.write(f'  🛠  Запчастин: {len(data.get("parts", []))}')

    def display_statistics(self, stats, dry_run):
        """Виводить статистику імпорту"""
        self.stdout.write(f'\n{"="*80}')
        self.stdout.write(self.style.SUCCESS('СТАТИСТИКА ІМПОРТУ'))
        self.stdout.write(f'{"="*80}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  ТЕСТОВИЙ РЕЖИМ - дані НЕ збережені в БД\n'))
        
        self.stdout.write(f'📊 Оброблено файлів: {stats["processed"]}')
        self.stdout.write(self.style.SUCCESS(f'✅ Успішно: {stats["success"]}'))
        self.stdout.write(self.style.ERROR(f'❌ Помилок: {stats["errors"]}'))
        self.stdout.write(self.style.WARNING(f'⚠️  Пропущено: {stats["skipped"]}'))
        
        if not dry_run:
            self.stdout.write(f'\n📈 Створено в БД:')
            self.stdout.write(f'  👤 Клієнтів: {stats["clients_created"]}')
            self.stdout.write(f'  🚗 Вантажівок: {stats["trucks_created"]}')
            self.stdout.write(f'  📋 Нарядів: {stats["orders_created"]}')
            self.stdout.write(f'  🔧 Робіт: {stats["works_created"]}')
            self.stdout.write(f'  🛠  Запчастин: {stats["parts_created"]}')
        
        self.stdout.write(f'{"="*80}\n')