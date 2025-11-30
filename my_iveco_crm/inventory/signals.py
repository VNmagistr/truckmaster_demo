from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import UsedPart, Stock


@receiver([post_save, post_delete], sender=UsedPart)
def update_order_on_part_change(sender, instance, **kwargs):
    """
    Коли запчастина додається до роботи або видаляється,
    перераховуємо вартість замовлення.
    """
    instance.service_work.service_order.update_total_cost()


@receiver([post_save, post_delete], sender=Stock)
def update_part_stock(sender, instance, **kwargs):
    """
    Оновлює загальний залишок товару при зміні на складі.
    """
    from django.db.models import Sum
    
    # Розраховуємо новий загальний залишок
    total = instance.product.stock_items.aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    # Оновлюємо current_stock в Part
    if instance.product.current_stock != total:
        instance.product.__class__.objects.filter(
            pk=instance.product.pk
        ).update(current_stock=total)