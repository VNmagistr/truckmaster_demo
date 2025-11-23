from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ServiceWork

@receiver([post_save, post_delete], sender=ServiceWork)
def update_order_on_work_change(sender, instance, **kwargs):
    """
    Коли робота створюється, оновлюється або видаляється,
    перераховуємо вартість замовлення.
    """
    try:
        # Перевіряємо чи існує ще замовлення
        if instance.service_order_id and instance.service_order:
            instance.service_order.update_total_cost()
    except Exception:
        # Якщо замовлення вже видалено - ігноруємо
        pass