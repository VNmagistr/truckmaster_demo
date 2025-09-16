from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import UsedPart

@receiver([post_save, post_delete], sender=UsedPart)
def update_order_on_part_change(sender, instance, **kwargs):
    """
    Коли запчастина додається до роботи або видаляється,
    перераховуємо вартість замовлення.
    """
    instance.service_work.service_order.update_total_cost()
