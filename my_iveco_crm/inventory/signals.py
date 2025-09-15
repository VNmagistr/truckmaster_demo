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

@receiver(post_save, sender=UsedPart)
def deduct_stock_on_save(sender, instance, created, **kwargs):
    """
    Коли запис UsedPart СТВОРЮЄТЬСЯ, списуємо кількість зі складу.
    """
    if created:
        part = instance.part
        part.current_stock -= instance.quantity
        part.save(update_fields=['current_stock'])

@receiver(post_delete, sender=UsedPart)
def restore_stock_on_delete(sender, instance, **kwargs):
    """
    Коли запис UsedPart ВИДАЛЯЄТЬСЯ, повертаємо кількість на склад.
    """
    part = instance.part
    part.current_stock += instance.quantity
    part.save(update_fields=['current_stock'])