# clients/management/commands/parse_fp3.py

import os
import re
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from pathlib import Path


class Command(BaseCommand):
    help = 'Парсить файли .fp3 для пошуку пробігу при заміні оливи'

    def add_arguments(self, parser):
        parser.add_argument(
            'folder_path',
            type=str,
            help='Шлях до папки з .fp3 файлами'
        )
        parser.add_argument(
            '--plate',
            type=str,
            help='Номер автомобіля (тільки цифри, наприклад: 9744)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Показати всі файли з заміною оливи'
        )

    def handle(self, *args, **options):
        folder_path = options['folder_path']
        plate_number = options.get('plate')
        show_all = options.get('all', False)

        if not os.path.exists(folder_path):
            self.stdout.write(self.style.ERROR(f'Папка не знайдена: {folder_path}'))
            return

        # Знаходимо всі .fp3 файли (враховуємо обидва регістри розширення)
        fp3_files = list(Path(folder_path).glob('*.fp3')) + list(Path(folder_path).glob('*.FP3'))
        
        if not fp3_files:
            self.stdout.write(self.style.WARNING('Не знайдено .fp3 файлів у папці'))
            return

        self.stdout.write(self.style.SUCCESS(f'Знайдено {len(fp3_files)} файлів'))
        
        results = []

        for file_path in fp3_files:
            # Аналізуємо ім'я файлу
            file_info = self.parse_filename(file_path.name)
            
            # Якщо вказаний номер, фільтруємо
            if plate_number and not self.match_plate(file_info, plate_number):
                continue

            # Парсимо XML
            try:
                data = self.parse_fp3_file(file_path)
                
                if data:
                    # Перевіряємо чи була заміна оливи
                    oil_change = self.check_oil_change(data)
                    
                    if oil_change or show_all:
                        result = {
                            'file': file_path.name,
                            'plate': data.get('plate', 'Н/Д'),
                            'chassis': data.get('chassis', 'Н/Д'),
                            'mileage': data.get('mileage', 'Н/Д'),
                            # Баг 4: використовуємо дані з імені файлу як fallback
                            'date': data.get('date') or file_info.get('date') or 'Н/Д',
                            'model': data.get('model', 'Н/Д'),
                            'invoice': data.get('invoice') or file_info.get('invoice') or 'Н/Д',
                            'oil_change': oil_change,
                            'works': data.get('works', []),
                            'parts': data.get('parts', [])
                        }
                        results.append(result)
                        
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Помилка обробки файлу {file_path.name}: {e}')
                )

        # Виводимо результати
        self.display_results(results, plate_number)

    def parse_filename(self, filename):
        """Витягує інформацію з імені файлу"""
        # Приклад: 12484_володимир_М1_КПП_колодки_перід_9744_250923.fp3
        info = {
            'invoice': None,
            'plate_digits': None,
            'has_m1': False,
            'date': None
        }
        
        parts = filename.replace('.fp3', '').split('_')
        
        # Перша частина - номер рахунку
        if parts and parts[0].isdigit():
            info['invoice'] = parts[0]
        
        # Шукаємо М1
        if 'М1' in filename or 'M1' in filename:
            info['has_m1'] = True
        
        # Баг 1: шукаємо 4 цифри безпосередньо перед датою (6 цифр наприкінці)
        # Приклад: 12484_..._9744_250923.fp3 → знайде 9744, а не 1248
        plate_match = re.search(r'_(\d{4})_\d{6}\.fp3$', filename, re.IGNORECASE)
        if plate_match:
            info['plate_digits'] = plate_match.group(1)
        
        # Дата в кінці (6 цифр)
        date_match = re.search(r'(\d{6})\.fp3$', filename)
        if date_match:
            info['date'] = date_match.group(1)
        
        return info

    def match_plate(self, file_info, plate_number):
        """Перевіряє чи відповідає номер"""
        # Залишаємо тільки цифри
        plate_digits = re.sub(r'\D', '', plate_number)
        
        if file_info['plate_digits']:
            return file_info['plate_digits'] == plate_digits[-4:]
        
        return False

    def parse_fp3_file(self, file_path):
        """Парсить XML файл .fp3"""
        try:
            # Баг 5: файли можуть бути в cp1251 (Windows-1251) або utf-8
            raw = file_path.read_bytes()
            for encoding in ('utf-8', 'cp1251', 'utf-8-sig'):
                try:
                    content = raw.decode(encoding)
                    root = ET.fromstring(content)
                    break
                except (UnicodeDecodeError, ET.ParseError):
                    continue
            else:
                self.stdout.write(self.style.ERROR(f'Не вдалося визначити кодування: {file_path.name}'))
                return None
            
            data = {
                'plate': None,
                'chassis': None,
                'mileage': None,
                'date': None,
                'model': None,
                'invoice': None,
                'works': [],
                'parts': []
            }
            
            # Шукаємо <page0>
            page0 = root.find('.//page0')
            if not page0:
                return None

            # Баг 2: будуємо parent_map один раз, щоб уникнути O(n²) пошуку
            parent_map = {child: parent for parent in page0.iter() for child in parent}

            # Витягуємо дані з елементів
            for elem in page0.iter():
                if 'u' in elem.attrib:
                    text = elem.attrib['u']
                    
                    # Номер рахунку
                    if 'Рахунок-фактура №' in text:
                        invoice_match = re.search(r'№\s*(\d+)', text)
                        if invoice_match:
                            data['invoice'] = invoice_match.group(1)
                    
                    # Баг 3: дата — беремо тільки перший збіг, щоб не перезаписувати
                    if not data['date'] and 'від' in text and 'р.' in text:
                        data['date'] = text.replace('від ', '').replace(' р.', '')
                    
                    # Модель
                    if elem.tag == 'm38' or (len(text) < 20 and re.match(r'^\d+[А-Я]\d+', text)):
                        if not data['model']:
                            data['model'] = text
                    
                    # Держномер
                    if elem.tag == 'm39':
                        data['plate'] = text
                    elif re.match(r'^[А-Я]{2}\d{4}[А-Я]{2}$', text):
                        data['plate'] = text
                    
                    # Шасі (VIN)
                    if elem.tag == 'm40':
                        data['chassis'] = text
                    elif len(text) == 7 and text.isdigit():
                        if not data['chassis']:
                            data['chassis'] = text
                    
                    # Пробіг
                    if elem.tag == 'm41':
                        # Видаляємо пробіли з числа
                        mileage = text.replace(' ', '').replace(',', '')
                        if mileage.isdigit():
                            data['mileage'] = mileage
                    
                    # Роботи та запчастини
                    if elem.tag == 'm1':
                        # Це назва роботи/запчастини
                        item_name = text

                        # Баг 2: використовуємо готовий parent_map замість O(n²) циклу
                        parent = parent_map.get(elem)

                        if parent:
                            unit = None
                            qty = None
                            
                            for child in parent:
                                if child.tag == 'm2' and 'u' in child.attrib:
                                    unit = child.attrib['u']
                                elif child.tag == 'm3' and 'u' in child.attrib:
                                    qty = child.attrib['u']
                            
                            item_data = {
                                'name': item_name,
                                'unit': unit,
                                'quantity': qty
                            }
                            
                            # Розділяємо на роботи та запчастини
                            if unit in ['годин', 'год', 'год.']:
                                data['works'].append(item_data)
                            else:
                                data['parts'].append(item_data)
            
            return data
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Помилка парсингу: {e}'))
            return None

    def check_oil_change(self, data):
        """Перевіряє чи була заміна оливи"""
        if not data or not data.get('works'):
            return False
        
        oil_keywords = [
            'оливи в двигуні',
            'оливи двигун',
            'олива двигун',
            'заміна масла',
            'М1',
            'ТО',
            'техобслуговування'
        ]
        
        for work in data['works']:
            work_name = work['name'].lower()
            if any(keyword.lower() in work_name for keyword in oil_keywords):
                return True
        
        # Також перевіряємо запчастини
        for part in data.get('parts', []):
            part_name = part['name'].lower()
            if 'олива моторна' in part_name or 'масло моторне' in part_name:
                return True
        
        return False

    def display_results(self, results, plate_number):
        """Виводить результати"""
        if not results:
            self.stdout.write(
                self.style.WARNING(
                    f'Не знайдено даних про заміну оливи'
                    + (f' для номера {plate_number}' if plate_number else '')
                )
            )
            return
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*80}'))
        self.stdout.write(self.style.SUCCESS(f'Знайдено записів: {len(results)}'))
        self.stdout.write(self.style.SUCCESS(f'{"="*80}\n'))
        
        for i, result in enumerate(results, 1):
            self.stdout.write(self.style.SUCCESS(f'\n--- Запис #{i} ---'))
            self.stdout.write(f'📄 Файл: {result["file"]}')
            self.stdout.write(f'🚗 Держномер: {result["plate"]}')
            self.stdout.write(f'🔧 Модель: {result["model"]}')
            self.stdout.write(f'🆔 Шасі: {result["chassis"]}')
            self.stdout.write(f'📊 Пробіг: {result["mileage"]} км')
            self.stdout.write(f'📅 Дата: {result["date"]}')
            self.stdout.write(f'📋 Рахунок: {result["invoice"]}')
            
            if result['oil_change']:
                self.stdout.write(self.style.SUCCESS('✅ Заміна оливи: ТАК'))
            
            if result['works']:
                self.stdout.write(f'\n🔧 Роботи:')
                for work in result['works']:
                    self.stdout.write(f"   - {work['name']} ({work['quantity']} {work['unit']})")
            
            if result['parts']:
                self.stdout.write(f'\n🛠 Запчастини:')
                for part in result['parts'][:5]:
                    self.stdout.write(f"   - {part['name']} ({part['quantity']} {part['unit']})")
                if len(result['parts']) > 5:
                    self.stdout.write(f"   ... і ще {len(result['parts']) - 5} позицій")
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*80}\n'))