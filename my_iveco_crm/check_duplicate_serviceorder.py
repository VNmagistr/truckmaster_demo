import os
import re

orders_models = r"D:\truckmaster\my_iveco_crm\orders\models.py"

if os.path.exists(orders_models):
    with open(orders_models, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
        
        print("=" * 70)
        print("ПОШУК ОГОЛОШЕНЬ ServiceOrder")
        print("=" * 70)
        
        serviceorder_classes = []
        
        for i, line in enumerate(lines, 1):
            if re.match(r'^\s*class\s+ServiceOrder\s*\(', line):
                serviceorder_classes.append(i)
                print(f"\nЗнайдено на рядку {i}:")
                
                # Показуємо контекст
                start = max(0, i - 3)
                end = min(len(lines), i + 10)
                
                for j in range(start, end):
                    marker = ">>>" if j == i - 1 else "   "
                    print(f"{marker} {j+1:3d}: {lines[j]}")
        
        print("\n" + "=" * 70)
        print("РЕЗУЛЬТАТ")
        print("=" * 70)
        
        if len(serviceorder_classes) == 0:
            print("❌ Клас ServiceOrder НЕ ЗНАЙДЕНО!")
        elif len(serviceorder_classes) == 1:
            print(f"✅ Клас ServiceOrder оголошено 1 раз (рядок {serviceorder_classes[0]})")
        else:
            print(f"❌ ПРОБЛЕМА: Клас ServiceOrder оголошено {len(serviceorder_classes)} разів!")
            print(f"   Рядки: {serviceorder_classes}")
            print("   ВИДАЛІТЬ ДУБЛІКАТИ!")