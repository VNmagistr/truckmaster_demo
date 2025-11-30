import os
import re

print("=" * 70)
print("ДІАГНОСТИКА ІМПОРТІВ ServiceOrder")
print("=" * 70)

base_path = r"D:\truckmaster\my_iveco_crm"

# Файли для перевірки
files_to_check = []
for root, dirs, files in os.walk(base_path):
    # Пропускаємо venv, migrations, __pycache__
    if any(skip in root for skip in ['venv', 'migrations', '__pycache__', '.git']):
        continue
    for file in files:
        if file.endswith('.py'):
            files_to_check.append(os.path.join(root, file))

print(f"\nПеревіряю {len(files_to_check)} Python файлів...\n")

problems = []

for filepath in files_to_check:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Шукаємо імпорти ServiceOrder
                if 'from orders.models import' in line and 'ServiceOrder' in line:
                    problems.append({
                        'file': filepath.replace(base_path, ''),
                        'line': i,
                        'content': line.strip(),
                        'type': 'IMPORT'
                    })
                
                # Шукаємо ForeignKey(ServiceOrder без лапок
                if 'ForeignKey' in line and 'ServiceOrder' in line:
                    if "'ServiceOrder'" not in line and '"ServiceOrder"' not in line:
                        if 'orders.ServiceOrder' not in line or ("'" not in line and '"' not in line):
                            problems.append({
                                'file': filepath.replace(base_path, ''),
                                'line': i,
                                'content': line.strip(),
                                'type': 'FOREIGNKEY'
                            })
    except Exception as e:
        print(f"Помилка читання {filepath}: {e}")

if problems:
    print("❌ ЗНАЙДЕНІ ПРОБЛЕМИ:\n")
    for p in problems:
        print(f"Тип: {p['type']}")
        print(f"Файл: {p['file']}")
        print(f"Рядок {p['line']}: {p['content']}")
        print("-" * 70)
else:
    print("✅ Проблем з імпортами ServiceOrder не знайдено\n")

print("\n" + "=" * 70)
print("ПЕРЕВІРКА __init__.py ФАЙЛІВ")
print("=" * 70)

init_files = [
    os.path.join(base_path, 'orders', '__init__.py'),
    os.path.join(base_path, 'inventory', '__init__.py'),
    os.path.join(base_path, 'clients', '__init__.py'),
]

for init_file in init_files:
    print(f"\n{init_file.replace(base_path, '')}:")
    if os.path.exists(init_file):
        try:
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    print("  ⚠️  НЕ ПОРОЖНІЙ:")
                    print("  " + content[:200])
                else:
                    print("  ✅ ПОРОЖНІЙ - OK")
        except Exception as e:
            print(f"  ❌ Помилка читання: {e}")
    else:
        print("  ❌ НЕ ІСНУЄ")

print("\n" + "=" * 70)
print("ПЕРЕВІРКА inventory/models.py")
print("=" * 70)

inventory_models = os.path.join(base_path, 'inventory', 'models.py')
if os.path.exists(inventory_models):
    with open(inventory_models, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        print("\n📋 Перші 15 рядків (імпорти):")
        for i, line in enumerate(lines[:15], 1):
            if line.strip():
                prefix = "  ✅" if 'ServiceOrder' not in line else "  ⚠️ "
                print(f"{prefix} {i:3d}: {line.rstrip()}")
        
        print("\n📋 Рядки з 'service_order' в StockMovement:")
        in_stockmovement = False
        for i, line in enumerate(lines, 1):
            if 'class StockMovement' in line:
                in_stockmovement = True
            if in_stockmovement and 'service_order' in line.lower():
                prefix = "  ✅" if "'orders.ServiceOrder'" in line else "  ❌"
                print(f"{prefix} {i:3d}: {line.rstrip()}")
            if in_stockmovement and line.strip().startswith('class ') and 'StockMovement' not in line:
                break

print("\n" + "=" * 70)
print("ДІАГНОСТИКА ЗАВЕРШЕНА")
print("=" * 70)