import os

print("=" * 70)
print("ПЕРЕВІРКА apps.py ФАЙЛІВ")
print("=" * 70)

base_path = r"D:\truckmaster\my_iveco_crm"

apps_to_check = [
    ('orders', 'orders/apps.py'),
    ('inventory', 'inventory/apps.py'),
    ('clients', 'clients/apps.py'),
]

for app_name, rel_path in apps_to_check:
    full_path = os.path.join(base_path, rel_path)
    
    print(f"\n{'=' * 70}")
    print(f"{rel_path}")
    print('=' * 70)
    
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
            
            # Перевіряємо чи є ready() метод
            if 'def ready(self)' in content:
                print("\n⚠️  Є метод ready() - перевіряємо що він робить...")
                
                if 'import' in content and 'signals' in content:
                    print("   ✅ Імпортує signals")
                
                # Перевіряємо чи немає проблемних імпортів
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if 'from orders.models import' in line:
                        print(f"   ❌ ПРОБЛЕМА на рядку {i}: {line.strip()}")
            else:
                print("\n✅ Немає методу ready() - це OK")
    else:
        print(f"❌ Файл не існує")

print("\n" + "=" * 70)
print("ПЕРЕВІРКА orders/signals.py")
print("=" * 70)

signals_path = os.path.join(base_path, 'orders', 'signals.py')
if os.path.exists(signals_path):
    with open(signals_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        print("\nПерші 30 рядків (імпорти):\n")
        for i, line in enumerate(lines[:30], 1):
            if line.strip():
                marker = "⚠️ " if 'from inventory' in line or 'from clients' in line else "   "
                print(f"{marker} {i:3d}: {line.rstrip()}")
else:
    print("✅ Файл signals.py не існує - це нормально")

print("\n" + "=" * 70)
print("ПЕРЕВІРКА inventory/signals.py")
print("=" * 70)

inv_signals_path = os.path.join(base_path, 'inventory', 'signals.py')
if os.path.exists(inv_signals_path):
    with open(inv_signals_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        print("\nПерші 20 рядків (імпорти):\n")
        for i, line in enumerate(lines[:20], 1):
            if line.strip():
                marker = "⚠️ " if 'from orders' in line else "   "
                print(f"{marker} {i:3d}: {line.rstrip()}")
else:
    print("✅ Файл signals.py не існує")