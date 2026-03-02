from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import UsedPart, StockItem


@receiver([post_save, post_delete], sender=UsedPart)
def update_order_on_part_change(sender, instance, **kwargs):
    """
    Коли запчастина додається до роботи або видаляється,
    перераховуємо вартість замовлення.
    """
    try:
        if instance.service_work_id:
            instance.service_work.service_order.update_total_cost()
        elif instance.service_order_id:
            instance.service_order.update_total_cost()
    except Exception:
        pass  # service_work може бути вже каскадно видалений


@receiver([post_save, post_delete], sender=StockItem)
def update_part_stock(sender, instance, **kwargs):
    """
    Оновлює загальний залишок товару при зміні на складі.
    """
    from django.db.models import Sum

    # Розраховуємо новий загальний залишок
    total = instance.product.stock_items.aggregate(
        total=Sum('quantity')
    )['total'] or 0

    # Оновлюємо current_stock в Product
    if instance.product.current_stock != total:
        instance.product.__class__.objects.filter(
            pk=instance.product.pk
        ).update(current_stock=total)
