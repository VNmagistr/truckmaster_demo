import os
import shutil

base_path = r"D:\truckmaster\my_iveco_crm"

print("=" * 70)
print("ПОВНА ОЧИСТКА КЕШУ PYTHON")
print("=" * 70)

removed_count = 0
error_count = 0

# Видалення всіх __pycache__ папок
for root, dirs, files in os.walk(base_path):
    if '__pycache__' in dirs:
        pycache_path = os.path.join(root, '__pycache__')
        try:
            shutil.rmtree(pycache_path)
            print(f"✅ Видалено: {pycache_path.replace(base_path, '')}")
            removed_count += 1
        except Exception as e:
            print(f"❌ Помилка: {pycache_path.replace(base_path, '')} - {e}")
            error_count += 1

# Видалення всіх .pyc файлів
for root, dirs, files in os.walk(base_path):
    for file in files:
        if file.endswith('.pyc'):
            pyc_path = os.path.join(root, file)
            try:
                os.remove(pyc_path)
                print(f"✅ Видалено: {pyc_path.replace(base_path, '')}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Помилка: {pyc_path.replace(base_path, '')} - {e}")
                error_count += 1

print("\n" + "=" * 70)
print(f"РЕЗУЛЬТАТ: Видалено {removed_count} об'єктів, помилок: {error_count}")
print("=" * 70)

print("\nНАСТУПНИЙ КРОК:")
print("1. Закрийте ВСІ термінали")
print("2. Закрийте VSCode (якщо відкритий)")
print("3. Відкрийте НОВИЙ термінал")
print("4. Запустіть: python manage.py check")