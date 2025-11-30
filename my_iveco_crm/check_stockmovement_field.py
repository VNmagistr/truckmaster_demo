import os

inventory_models = r"D:\truckmaster\my_iveco_crm\inventory\models.py"

if os.path.exists(inventory_models):
    with open(inventory_models, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        print("=" * 70)
        print("ПОШУК service_order в StockMovement")
        print("=" * 70)
        
        in_class = False
        found_line = None
        
        for i, line in enumerate(lines, 1):
            if 'class StockMovement' in line:
                in_class = True
                print(f"\nКлас StockMovement знайдено на рядку {i}\n")
            
            if in_class and 'service_order' in line and 'ForeignKey' in line:
                found_line = i
                
                # Показуємо контекст
                start = max(0, i - 5)
                end = min(len(lines), i + 5)
                
                for j in range(start, end):
                    marker = ">>>" if j == i - 1 else "   "
                    print(f"{marker} {j+1:3d}: {lines[j].rstrip()}")
                
                # Аналізуємо рядок
                print("\n" + "=" * 70)
                print("АНАЛІЗ РЯДКА:")
                print("=" * 70)
                
                field_line = lines[i-1]
                
                # Перевіряємо варіанти
                if "'orders.ServiceOrder'" in field_line:
                    print("✅ ПРАВИЛЬНО: 'orders.ServiceOrder' (одинарні лапки)")
                elif '"orders.ServiceOrder"' in field_line:
                    print("✅ ПРАВИЛЬНО: \"orders.ServiceOrder\" (подвійні лапки)")
                elif "'ServiceOrder'" in field_line:
                    print("⚠️  ЧАСТКОВО: 'ServiceOrder' без app_label")
                    print("   Краще: 'orders.ServiceOrder'")
                elif '"ServiceOrder"' in field_line:
                    print("⚠️  ЧАСТКОВО: \"ServiceOrder\" без app_label")
                    print("   Краще: 'orders.ServiceOrder'")
                else:
                    print("❌ ПОМИЛКА: ServiceOrder без лапок!")
                    print("   Потрібно: 'orders.ServiceOrder'")
                
                break
            
            if in_class and line.strip().startswith('class ') and 'StockMovement' not in line:
                break
        
        if not found_line:
            print("⚠️  service_order ForeignKey не знайдено в StockMovement")

else:
    print(f"Файл не знайдено: {inventory_models}")