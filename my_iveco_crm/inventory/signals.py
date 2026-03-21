from django.db.models.signals import post_save, post_delete, pre_save
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


# --- Автоматичне списання запчастин зі складу ---

def _get_warehouse(instance):
    """Повертає склад для списання: явно вказаний або склад за замовчуванням."""
    from .models import Warehouse
    return instance.warehouse or Warehouse.objects.filter(is_default=True).first()


def _get_service_order(instance):
    """Витягує наряд-замовлення з UsedPart незалежно від того, через роботу чи напряму."""
    if instance.service_order_id:
        return instance.service_order
    if instance.service_work_id:
        try:
            return instance.service_work.service_order
        except Exception:
            pass
    return None


def _apply_stock_delta(instance, delta):
    """
    Змінює кількість на складі на `delta` (від'ємне — списання, додатне — повернення)
    і створює відповідний StockMovement.
    """
    from .models import StockMovement, Warehouse

    if delta == 0:
        return

    warehouse = _get_warehouse(instance)
    if not warehouse:
        return

    stock_item, _ = StockItem.objects.get_or_create(
        warehouse=warehouse,
        product=instance.part,
        defaults={'quantity': 0},
    )
    stock_item.quantity += delta
    stock_item.save()

    service_order = _get_service_order(instance)

    if delta < 0:
        StockMovement.objects.create(
            movement_type='out',
            product=instance.part,
            quantity=-delta,
            warehouse_from=warehouse,
            service_order=service_order,
            notes=f'Автоматичне списання з наряду {service_order}',
        )
    else:
        StockMovement.objects.create(
            movement_type='return',
            product=instance.part,
            quantity=delta,
            warehouse_to=warehouse,
            service_order=service_order,
            notes=f'Повернення на склад при зміні наряду {service_order}',
        )


@receiver(pre_save, sender=UsedPart)
def cache_old_used_part_quantity(sender, instance, **kwargs):
    """Зберігаємо стару кількість перед оновленням для розрахунку дельти."""
    if instance.pk:
        try:
            instance._old_quantity = UsedPart.objects.get(pk=instance.pk).quantity
        except UsedPart.DoesNotExist:
            instance._old_quantity = None
    else:
        instance._old_quantity = None


@receiver(post_save, sender=UsedPart)
def deduct_stock_on_used_part_save(sender, instance, created, **kwargs):
    """Списує або коригує кількість на складі при збереженні UsedPart."""
    if created:
        _apply_stock_delta(instance, -instance.quantity)
    else:
        old_qty = getattr(instance, '_old_quantity', None)
        if old_qty is not None:
            delta = old_qty - instance.quantity  # якщо збільшили кількість — дельта від'ємна
            _apply_stock_delta(instance, delta)


@receiver(post_delete, sender=UsedPart)
def restore_stock_on_used_part_delete(sender, instance, **kwargs):
    """Повертає запчастину на склад при видаленні UsedPart з наряду."""
    _apply_stock_delta(instance, +instance.quantity)
