import os
import sys

# Додаємо шлях до проекту
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'my_iveco_crm'))

# Налаштовуємо Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_iveco_crm.settings')

import django
django.setup()

print("=" * 60)
print("ДІАГНОСТИКА МОДЕЛЕЙ")
print("=" * 60)

# Перевірка ServiceOrder
try:
    from orders.models import ServiceOrder
    print("✅ orders.models.ServiceOrder імпортується успішно")
    print(f"   App label: {ServiceOrder._meta.app_label}")
    print(f"   Model name: {ServiceOrder._meta.model_name}")
except Exception as e:
    print(f"❌ Помилка імпорту ServiceOrder: {e}")

print()

# Перевірка StockMovement
try:
    from inventory.models import StockMovement
    print("✅ inventory.models.StockMovement імпортується успішно")
    print(f"   App label: {StockMovement._meta.app_label}")
    print(f"   Model name: {StockMovement._meta.model_name}")
    
    # Перевіряємо поле service_order
    service_order_field = StockMovement._meta.get_field('service_order')
    print(f"   Поле service_order:")
    print(f"   - Тип: {type(service_order_field)}")
    print(f"   - Related model: {service_order_field.related_model}")
    
except Exception as e:
    print(f"❌ Помилка з StockMovement: {e}")

print()

# Перевірка всіх зареєстрованих моделей
from django.apps import apps

print("Зареєстровані моделі orders:")
for model in apps.get_app_config('orders').get_models():
    print(f"  - {model._meta.model_name}")

print()
print("Зареєстровані моделі inventory:")
for model in apps.get_app_config('inventory').get_models():
    print(f"  - {model._meta.model_name}")

print()
print("=" * 60)
print("Перевірка завершена")
print("=" * 60)