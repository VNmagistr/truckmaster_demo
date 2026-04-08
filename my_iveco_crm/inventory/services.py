from .models import StockItem, StockMovement, Warehouse


def _get_warehouse(used_part):
    return used_part.warehouse or Warehouse.objects.filter(is_default=True).first()


def _get_service_order(used_part):
    if used_part.service_order_id:
        return used_part.service_order
    if used_part.service_work_id:
        try:
            return used_part.service_work.service_order
        except Exception:
            pass
    return None


class StockService:
    @staticmethod
    def deduct(used_part):
        """Списує кількість зі складу при додаванні UsedPart."""
        warehouse = _get_warehouse(used_part)
        if not warehouse:
            return
        stock_item, _ = StockItem.objects.get_or_create(
            warehouse=warehouse,
            product=used_part.part,
            defaults={'quantity': 0},
        )
        stock_item.quantity -= used_part.quantity
        stock_item.save()

        service_order = _get_service_order(used_part)
        StockMovement.objects.create(
            movement_type='out',
            product=used_part.part,
            quantity=used_part.quantity,
            warehouse_from=warehouse,
            service_order=service_order,
            notes=f'Списання з наряду {service_order}',
        )

    @staticmethod
    def restore(used_part):
        """Повертає кількість на склад при видаленні UsedPart."""
        warehouse = _get_warehouse(used_part)
        if not warehouse:
            return
        stock_item, _ = StockItem.objects.get_or_create(
            warehouse=warehouse,
            product=used_part.part,
            defaults={'quantity': 0},
        )
        stock_item.quantity += used_part.quantity
        stock_item.save()

        service_order = _get_service_order(used_part)
        StockMovement.objects.create(
            movement_type='return',
            product=used_part.part,
            quantity=used_part.quantity,
            warehouse_to=warehouse,
            service_order=service_order,
            notes=f'Повернення на склад при зміні наряду {service_order}',
        )

    @staticmethod
    def adjust(used_part, old_quantity):
        """Коригує залишок при зміні кількості UsedPart."""
        delta = old_quantity - used_part.quantity  # > 0 = повернення, < 0 = додаткове списання
        if delta == 0:
            return
        warehouse = _get_warehouse(used_part)
        if not warehouse:
            return
        stock_item, _ = StockItem.objects.get_or_create(
            warehouse=warehouse,
            product=used_part.part,
            defaults={'quantity': 0},
        )
        stock_item.quantity += delta
        stock_item.save()

        service_order = _get_service_order(used_part)
        if delta < 0:
            StockMovement.objects.create(
                movement_type='out',
                product=used_part.part,
                quantity=-delta,
                warehouse_from=warehouse,
                service_order=service_order,
                notes=f'Списання з наряду {service_order}',
            )
        else:
            StockMovement.objects.create(
                movement_type='return',
                product=used_part.part,
                quantity=delta,
                warehouse_to=warehouse,
                service_order=service_order,
                notes=f'Повернення на склад при зміні наряду {service_order}',
            )
