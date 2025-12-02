#!/usr/bin/env python3
"""
Скрипт для пошуку пробігу автомобіля при заміні оливи в .fp3 файлах

Використання:
    python search_mileage.py /шлях/до/папки 9744
    python search_mileage.py /шлях/до/папки --all  # показати всі з заміною оливи
"""

import os
import sys
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime


def extract_plate_from_filename(filename):
    """Витягує цифри номера з імені файлу"""
    # Шукаємо 4 цифри підряд (наприклад 9744)
    match = re.search(r'_(\d{4})_', filename)
    if match:
        return match.group(1)
    return None


def has_m1_in_filename(filename):
    """Перевіряє наявність М1 в імені файлу"""
    return 'М1' in filename.upper() or 'M1' in filename.upper()


def parse_fp3_quick(file_path):
    """Швидкий парсинг тільки необхідних даних"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        data = {
            'plate': None,
            'chassis': None,
            'mileage': None,
            'date': None,
            'model': None,
            'has_oil_change': False
        }
        
        # Шукаємо всі елементи з атрибутом 'u'
        for elem in root.iter():
            if 'u' not in elem.attrib:
                continue
            
            text = elem.attrib['u']
            
            # Держномер (формат АС9744СК)
            if re.match(r'^[А-Я]{2}\d{4}[А-Я]{2}$', text):
                data['plate'] = text
            
            # Шасі (7 цифр)
            elif len(text) == 7 and text.isdigit():
                if not data['chassis']:
                    data['chassis'] = text
            
            # Пробіг (число з пробілами: "441 264")
            elif re.match(r'^\d{3,}\s*\d{3}$', text):
                data['mileage'] = text.replace(' ', '')
            
            # Модель (формат 70С17)
            elif re.match(r'^\d{2}[А-Я]\d{2}$', text):
                if not data['model']:
                    data['model'] = text
            
            # Дата
            elif 'від' in text and ('вересня' in text or 'січня' in text or 
                                   'лютого' in text or 'березня' in text or
                                   'квітня' in text or 'травня' in text or
                                   'червня' in text or 'липня' in text or
                                   'серпня' in text or 'жовтня' in text or
                                   'листопада' in text or 'грудня' in text):
                data['date'] = text.replace('від ', '').replace(' р.', '')
            
            # Заміна оливи
            if 'оливи в двигуні' in text.lower() or 'олива моторна' in text.lower():
                data['has_oil_change'] = True
        
        return data
        
    except Exception as e:
        print(f"❌ Помилка парсингу {file_path.name}: {e}")
        return None


def format_date(date_str):
    """Форматує дату для сортування"""
    months = {
        'січня': 1, 'лютого': 2, 'березня': 3, 'квітня': 4,
        'травня': 5, 'червня': 6, 'липня': 7, 'серпня': 8,
        'вересня': 9, 'жовтня': 10, 'листопада': 11, 'грудня': 12
    }
    
    try:
        # "25 вересня 2023"
        parts = date_str.split()
        day = int(parts[0])
        month = months.get(parts[1], 1)
        year = int(parts[2])
        return datetime(year, month, day)
    except:
        return datetime(1900, 1, 1)


def search_by_plate(folder, plate_number):
    """Шукає файли по номеру автомобіля"""
    folder_path = Path(folder)
    
    if not folder_path.exists():
        print(f"❌ Папка не існує: {folder}")
        return
    
    # Залишаємо тільки цифри з номера
    plate_digits = re.sub(r'\D', '', plate_number)
    
    print(f"\n🔍 Шукаю файли для номера, що містить: {plate_digits}")
    print(f"📁 Папка: {folder}")
    print("="*80)
    
    fp3_files = list(folder_path.glob('*.fp3'))
    
    if not fp3_files:
        print("❌ Не знайдено .fp3 файлів у папці")
        return
    
    print(f"📊 Всього файлів: {len(fp3_files)}\n")
    
    results = []
    
    for file_path in fp3_files:
        # Метод 1: По назві файлу
        file_plate = extract_plate_from_filename(file_path.name)
        file_has_m1 = has_m1_in_filename(file_path.name)
        
        if file_plate and plate_digits in file_plate:
            print(f"✅ Знайдено співпадіння в імені: {file_path.name}")
            
            # Парсимо файл
            data = parse_fp3_quick(file_path)
            
            if data:
                data['filename'] = file_path.name
                data['file_has_m1'] = file_has_m1
                results.append(data)
    
    # Сортуємо по даті
    results.sort(key=lambda x: format_date(x.get('date', '')))
    
    # Виводимо результати
    print("\n" + "="*80)
    print(f"📋 РЕЗУЛЬТАТИ (знайдено {len(results)} записів)")
    print("="*80 + "\n")
    
    oil_changes = [r for r in results if r['has_oil_change']]
    
    if oil_changes:
        print(f"🛢️  ЗАМІНИ ОЛИВИ ({len(oil_changes)} записів):\n")
        
        for i, r in enumerate(oil_changes, 1):
            print(f"{i}. 📅 {r.get('date', 'Н/Д')}")
            print(f"   🚗 Номер: {r.get('plate', 'Н/Д')}")
            print(f"   📊 Пробіг: {r.get('mileage', 'Н/Д')} км")
            print(f"   🔧 Модель: {r.get('model', 'Н/Д')}")
            print(f"   🆔 Шасі: {r.get('chassis', 'Н/Д')}")
            print(f"   📄 Файл: {r.get('filename', 'Н/Д')}")
            print()
    
    other_records = [r for r in results if not r['has_oil_change']]
    
    if other_records:
        print(f"\n📝 ІНШІ РОБОТИ ({len(other_records)} записів):\n")
        
        for i, r in enumerate(other_records, 1):
            print(f"{i}. 📅 {r.get('date', 'Н/Д')} | 📊 {r.get('mileage', 'Н/Д')} км | {r.get('filename', 'Н/Д')}")


def show_all_oil_changes(folder):
    """Показує всі заміни оливи в папці"""
    folder_path = Path(folder)
    
    if not folder_path.exists():
        print(f"❌ Папка не існує: {folder}")
        return
    
    print(f"\n🔍 Шукаю всі заміни оливи")
    print(f"📁 Папка: {folder}")
    print("="*80)
    
    fp3_files = list(folder_path.glob('*.fp3'))
    print(f"📊 Всього файлів: {len(fp3_files)}\n")
    
    results = []
    
    for file_path in fp3_files:
        data = parse_fp3_quick(file_path)
        
        if data and data['has_oil_change']:
            data['filename'] = file_path.name
            results.append(data)
    
    # Сортуємо по даті
    results.sort(key=lambda x: format_date(x.get('date', '')))
    
    print("\n" + "="*80)
    print(f"📋 ЗНАЙДЕНО ЗАМІН ОЛИВИ: {len(results)}")
    print("="*80 + "\n")
    
    for i, r in enumerate(results, 1):
        print(f"{i}. 📅 {r.get('date', 'Н/Д')}")
        print(f"   🚗 Номер: {r.get('plate', 'Н/Д')}")
        print(f"   📊 Пробіг: {r.get('mileage', 'Н/Д')} км")
        print(f"   🔧 Модель: {r.get('model', 'Н/Д')}")
        print(f"   📄 Файл: {r.get('filename', 'Н/Д')}")
        print()


def main():
    if len(sys.argv) < 2:
        print("❌ Використання:")
        print("   python search_mileage.py /шлях/до/папки 9744")
        print("   python search_mileage.py /шлях/до/папки --all")
        sys.exit(1)
    
    folder = sys.argv[1]
    
    if len(sys.argv) > 2 and sys.argv[2] == '--all':
        show_all_oil_changes(folder)
    elif len(sys.argv) > 2:
        plate_number = sys.argv[2]
        search_by_plate(folder, plate_number)
    else:
        print("❌ Вкажіть номер автомобіля або --all")
        sys.exit(1)


if __name__ == '__main__':
    main()
    