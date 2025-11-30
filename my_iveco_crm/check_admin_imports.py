import os
import re

print("=" * 70)
print("ПОШУК ПРОБЛЕМНИХ ІМПОРТІВ В ADMIN.PY")
print("=" * 70)

base_path = r"D:\truckmaster\my_iveco_crm"

admin_files = [
    'orders/admin.py',
    'inventory/admin.py',
    'clients/admin.py',
]

for rel_path in admin_files:
    full_path = os.path.join(base_path, rel_path)
    
    print(f"\n{'=' * 70}")
    print(f"{rel_path}")
    print('=' * 70)
    
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            print("\nІмпорти (перші 30 рядків):\n")
            
            problems = []
            for i, line in enumerate(lines[:30], 1):
                if line.strip() and not line.strip().startswith('#'):
                    # Перевіряємо cross-imports
                    marker = "   "
                    
                    if rel_path == 'orders/admin.py':
                        if 'from inventory' in line or 'from clients' in line:
                            marker = "⚠️ "
                            problems.append((i, line.strip()))
                    
                    elif rel_path == 'inventory/admin.py':
                        if 'from orders' in line or 'from clients' in line:
                            marker = "⚠️ "
                            problems.append((i, line.strip()))
                    
                    elif rel_path == 'clients/admin.py':
                        if 'from orders' in line or 'from inventory' in line:
                            marker = "⚠️ "
                            problems.append((i, line.strip()))
                    
                    print(f"{marker} {i:3d}: {line.rstrip()}")
            
            if problems:
                print(f"\n❌ Знайдено {len(problems)} потенційних проблем(и)")
            else:
                print("\n✅ Немає cross-imports")
    else:
        print(f"❌ Файл не існує")

print("\n" + "=" * 70)
print("ДЕТАЛЬНА ПЕРЕВІРКА inventory/admin.py")
print("=" * 70)

inventory_admin = os.path.join(base_path, 'inventory', 'admin.py')
if os.path.exists(inventory_admin):
    with open(inventory_admin, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # Шукаємо клас StockMovementAdmin
        if 'class StockMovementAdmin' in content:
            lines = content.split('\n')
            in_class = False
            
            print("\nКлас StockMovementAdmin:\n")
            
            for i, line in enumerate(lines, 1):
                if 'class StockMovementAdmin' in line:
                    in_class = True
                
                if in_class:
                    print(f"{i:3d}: {line}")
                    
                    if line.strip().startswith('class ') and 'StockMovementAdmin' not in line:
                        break

print("\n" + "=" * 70)
print("РЕКОМЕНДАЦІЇ")
print("=" * 70)
print("""
Якщо в admin.py є імпорти з інших додатків на рівні модуля,
це може викликати циклічний імпорт при завантаженні Django Admin.

ВИРІШЕННЯ:
- Видалити cross-imports з admin.py
- Використовувати autocomplete_fields замість прямих посилань на моделі
- Використовувати строкові посилання ('app.Model') де можливо
""")