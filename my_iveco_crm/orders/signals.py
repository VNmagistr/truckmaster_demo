from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ServiceWork, MaintenanceKit
# ❌ ВИДАЛЕНО: from inventory.models import UsedPart
import logging

logger = logging.getLogger(__name__)


@receiver([post_save, post_delete], sender=ServiceWork)
def update_order_on_work_change(sender, instance, **kwargs):
    """
    Коли робота створюється, оновлюється або видаляється,
    перераховуємо вартість замовлення.
    """
    try:
        if instance.service_order_id and instance.service_order:
            instance.service_order.update_total_cost()
    except Exception as e:
        logger.debug(f"Не вдалося оновити вартість: {e}")


@receiver(post_save, sender=ServiceWork)
def auto_add_maintenance_kit(sender, instance, created, **kwargs):
    """
    При створенні роботи типу 'ТО' або 'Заміна оливи'
    автоматично додає запчастини з набору ТО для цього авто.
    """
    # ✅ ЛОКАЛЬНИЙ ІМПОРТ всередині функції!
    from inventory.models import UsedPart
    
    if not created:
        return  # Тільки при створенні нової роботи
    
    # Перевіряємо чи є вантажівка в замовленні
    truck = instance.service_order.truck
    if not truck:
        return
    
    # Перевіряємо чи робота пов'язана з ТО (по назві категорії або роботи)
    work = instance.work
    if not work:
        return
    
    # Ключові слова для визначення робіт ТО
    to_keywords = ['то ', 'т.о.', 'заміна оливи', 'заміна масла', 'регламент', 'технічне обслуговування']
    
    work_name_lower = work.name.lower()
    group_name_lower = work.work_group.name.lower() if work.work_group else ''
    
    is_maintenance_work = any(
        keyword in work_name_lower or keyword in group_name_lower 
        for keyword in to_keywords
    )
    
    if not is_maintenance_work:
        return  # Це не робота ТО, пропускаємо
    
    # Шукаємо набір ТО для цієї вантажівки
    try:
        kit = MaintenanceKit.objects.get(truck=truck)
    except MaintenanceKit.DoesNotExist:
        logger.info(f"Набір ТО для {truck.license_plate} не знайдено")
        return
    
    # Додаємо оливу
    if kit.oil:
        UsedPart.objects.get_or_create(
            service_work=instance,
            part=kit.oil,
            defaults={'quantity': int(kit.oil_quantity)}
        )
    
    # Додаємо всі фільтри з набору
    for kit_filter in kit.filters.all():
        UsedPart.objects.get_or_create(
            service_work=instance,
            part=kit_filter.part,
            defaults={'quantity': kit_filter.quantity}
        )
    
    logger.info(f"Автоматично додано набір ТО для {truck.license_plate}")
    
    # Оновлюємо вартість замовлення
    instance.service_order.update_total_cost()