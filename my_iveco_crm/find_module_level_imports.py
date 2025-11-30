import os
import re

print("=" * 70)
print("ПОШУК ІМПОРТІВ ServiceOrder НА РІВНІ МОДУЛЯ")
print("=" * 70)

base_path = r"D:\truckmaster\my_iveco_crm"

# Файли які НЕ мають імпортувати ServiceOrder на верхньому рівні
critical_files = [
    'inventory/models.py',
    'inventory/admin.py', 
    'inventory/views.py',
    'inventory/serializers.py',
    'clients/models.py',
    'clients/admin.py',
]

print("\nПеревірка критичних файлів:\n")

for rel_path in critical_files:
    full_path = os.path.join(base_path, rel_path)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            has_problem = False
            for i, line in enumerate(lines[:30], 1):  # Перші 30 рядків
                # Шукаємо імпорт ServiceOrder на верхньому рівні
                if re.match(r'^\s*from\s+orders\.models\s+import.*ServiceOrder', line):
                    print(f"❌ {rel_path}")
                    print(f"   Рядок {i}: {line.strip()}")
                    has_problem = True
                    break
            
            if not has_problem:
                print(f"✅ {rel_path} - OK")
    else:
        print(f"⚠️  {rel_path} - файл не існує")

print("\n" + "=" * 70)
print("ПЕРЕВІРКА clients/models.py ДЕТАЛЬНО")
print("=" * 70)

clients_models = os.path.join(base_path, 'clients', 'models.py')
if os.path.exists(clients_models):
    with open(clients_models, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
        
        # Шукаємо клас Truck і метод get_latest_mileage
        in_truck = False
        in_method = False
        
        for i, line in enumerate(lines, 1):
            if 'class Truck' in line:
                in_truck = True
                print(f"\nЗнайдено клас Truck на рядку {i}")
            
            if in_truck and 'def get_latest_mileage' in line:
                in_method = True
                print(f"Знайдено метод get_latest_mileage на рядку {i}")
                
                # Показуємо наступні 10 рядків
                print("\nКонтекст методу:")
                for j in range(i-1, min(i+10, len(lines))):
                    marker = ">>>" if 'ServiceOrder' in lines[j] else "   "
                    print(f"{marker} {j+1:3d}: {lines[j]}")
                break

print("\n" + "=" * 70)
print("РЕКОМЕНДАЦІЇ")
print("=" * 70)

print("""
Якщо знайдено імпорт ServiceOrder в clients/models.py:

НЕПРАВИЛЬНО (на рівні модуля):
    from orders.models import ServiceOrder  # ← На початку файлу
    
    class Truck:
        def get_latest_mileage(self):
            order_mileage = ServiceOrder.objects.filter(...)

ПРАВИЛЬНО (локальний імпорт):
    # НЕ імпортуємо на початку файлу
    
    class Truck:
        def get_latest_mileage(self):
            from orders.models import ServiceOrder  # ← Всередині методу
            order_mileage = ServiceOrder.objects.filter(...)
""")