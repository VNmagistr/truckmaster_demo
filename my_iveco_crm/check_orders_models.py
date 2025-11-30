import os

orders_models = r"D:\truckmaster\my_iveco_crm\orders\models.py"

if os.path.exists(orders_models):
    with open(orders_models, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        print("=" * 70)
        print("ПОШУК ПРОБЛЕМ В orders/models.py")
        print("=" * 70)
        
        # Шукаємо всі ForeignKey до ServiceOrder
        problems = []
        
        for i, line in enumerate(lines, 1):
            if 'ForeignKey' in line and 'ServiceOrder' in line:
                # Перевіряємо чи є лапки
                if "'ServiceOrder'" not in line and '"ServiceOrder"' not in line:
                    problems.append({
                        'line': i,
                        'content': line.strip()
                    })
        
        if problems:
            print("\n❌ ЗНАЙДЕНІ ПРОБЛЕМИ (ForeignKey без лапок):\n")
            for p in problems:
                print(f"Рядок {p['line']}:")
                print(f"  {p['content']}")
                
                # Показуємо контекст
                start = max(0, p['line'] - 3)
                end = min(len(lines), p['line'] + 2)
                print("\n  Контекст:")
                for j in range(start, end):
                    marker = ">>>" if j == p['line'] - 1 else "   "
                    print(f"  {marker} {j+1:3d}: {lines[j].rstrip()}")
                print("-" * 70)
        else:
            print("\n✅ Всі ForeignKey до ServiceOrder написані правильно (в лапках)")
        
        # Перевіряємо імпорти на початку файлу
        print("\n" + "=" * 70)
        print("ІМПОРТИ (перші 20 рядків):")
        print("=" * 70)
        
        for i, line in enumerate(lines[:20], 1):
            if line.strip():
                marker = "⚠️ " if 'import' in line.lower() else "   "
                print(f"{marker} {i:3d}: {line.rstrip()}")
        
else:
    print(f"Файл не знайдено: {orders_models}")