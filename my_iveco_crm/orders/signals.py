import asyncio
import logging
import os

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .models import ServiceWork, MaintenanceKit, MaintenanceKitFilter, ServiceOrder, RepairPhoto

logger = logging.getLogger(__name__)

# Типи категорій, що вважаються оливою
OIL_CATEGORY_TYPES = {'oil', 'олива', 'масло', 'мастило'}

TO_KEYWORDS = ['то ', 'т.о.', 'заміна оливи', 'заміна масла', 'регламент', 'технічне обслуговування']


def _is_maintenance_work(work):
    """Перевіряє чи є робота технічним обслуговуванням."""
    if not work:
        return False
    name = work.name.lower()
    group = work.work_group.name.lower() if work.work_group else ''
    return any(kw in name or kw in group for kw in TO_KEYWORDS)


def _is_oil_product(product):
    """Перевіряє чи є товар оливою по типу категорії."""
    try:
        return product.subcategory.category.category_type.lower() in OIL_CATEGORY_TYPES
    except AttributeError:
        return False


@receiver(pre_save, sender=ServiceOrder)
def capture_old_status(sender, instance, update_fields, **kwargs):
    """
    Перед збереженням запам'ятовує поточний статус замовлення.
    Якщо оновлюються конкретні поля і статус серед них — пропускаємо зайвий SELECT.
    """
    if update_fields is not None and 'status' not in update_fields:
        instance._previous_status = None
        return
    if instance.pk:
        try:
            instance._previous_status = ServiceOrder.objects.only('status').get(pk=instance.pk).status
        except ServiceOrder.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender=ServiceOrder)
def record_status_change(sender, instance, created, **kwargs):
    """
    Після збереження фіксує зміну статусу в OrderStatusHistory.
    При створенні — записує початковий статус.
    При оновленні — записує лише якщо статус змінився.
    """
    from .models import OrderStatusHistory

    changed_by = getattr(instance, '_changed_by', None)

    if created:
        OrderStatusHistory.objects.create(
            order=instance,
            from_status='',
            to_status=instance.status,
            changed_by=changed_by,
        )
        return

    previous_status = getattr(instance, '_previous_status', None)
    if previous_status is not None and previous_status != instance.status:
        OrderStatusHistory.objects.create(
            order=instance,
            from_status=previous_status,
            to_status=instance.status,
            changed_by=changed_by,
        )


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
    автоматично додає запчастини з існуючого набору ТО для цього авто.
    """
    from inventory.models import UsedPart

    if not created:
        return

    truck = instance.service_order.truck
    if not truck or not _is_maintenance_work(instance.work):
        return

    try:
        kit = MaintenanceKit.objects.get(truck=truck)
    except MaintenanceKit.DoesNotExist:
        logger.info(f"Набір ТО для {truck.license_plate} не знайдено")
        return

    if kit.oil:
        UsedPart.objects.get_or_create(
            service_work=instance,
            part=kit.oil,
            defaults={'quantity': int(kit.oil_quantity)}
        )

    for kit_filter in kit.filters.all():
        UsedPart.objects.get_or_create(
            service_work=instance,
            part=kit_filter.part,
            defaults={'quantity': kit_filter.quantity}
        )

    logger.info(f"Автоматично додано набір ТО для {truck.license_plate}")
    instance.service_order.update_total_cost()


@receiver(post_save, sender=RepairPhoto)
def notify_client_on_new_photo(sender, instance, created, **kwargs):
    """
    Після додавання фото ремонту надсилає сповіщення клієнту в Telegram,
    якщо у нього є telegram_chat_id.
    """
    if not created:
        return

    client = instance.service_order.client
    if not client or not client.telegram_chat_id:
        return

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return

    try:
        from telegram import Bot
        order = instance.service_order
        text = (
            f"📸 *Нове фото ремонту*\n\n"
            f"Замовлення: №{order.order_number}\n"
            f"Автомобіль: {order.truck.license_plate}\n\n"
            f"Переглянути деталі у особистому кабінеті:\n"
            f"https://ital-truck.com.ua/cabinet/orders/{order.id}"
        )
        bot = Bot(token=bot_token)
        asyncio.run(bot.send_message(
            chat_id=client.telegram_chat_id,
            text=text,
            parse_mode='Markdown',
        ))
    except Exception as e:
        logger.error(f"Помилка сповіщення клієнта {client.id} про фото: {e}")


def auto_save_maintenance_kit(sender, instance, created, **kwargs):
    # Підключається вручну в orders/apps.py після завантаження всіх застосунків
    """
    Коли до роботи ТО додається запчастина — автоматично зберігає/оновлює
    набір ТО для цього автомобіля, щоб використовувати його в майбутніх нарядах.

    Логіка:
    - Олива (category_type in OIL_CATEGORY_TYPES) → створює/оновлює MaintenanceKit,
      плюс додає всі вже наявні фільтри з цієї роботи.
    - Фільтр → якщо kit вже існує, додає/оновлює MaintenanceKitFilter.
    """
    if not created or not instance.service_work:
        return

    work = instance.service_work
    if not _is_maintenance_work(work.work):
        return

    truck = work.service_order.truck
    if not truck:
        return

    part = instance.part

    try:
        if _is_oil_product(part):
            # Створюємо або оновлюємо kit з оливою
            kit, _ = MaintenanceKit.objects.update_or_create(
                truck=truck,
                defaults={'oil': part, 'oil_quantity': instance.quantity}
            )
            # Додаємо всі вже збережені фільтри з цієї роботи до kit
            for used_part in work.used_parts.exclude(pk=instance.pk):
                if not _is_oil_product(used_part.part):
                    MaintenanceKitFilter.objects.get_or_create(
                        maintenance_kit=kit,
                        part=used_part.part,
                        defaults={'quantity': used_part.quantity}
                    )
            logger.info(f"Збережено оливу '{part}' у наборі ТО для {truck.license_plate}")
        else:
            # Це фільтр — додаємо до існуючого kit
            kit = MaintenanceKit.objects.filter(truck=truck).first()
            if kit:
                obj, created_filter = MaintenanceKitFilter.objects.get_or_create(
                    maintenance_kit=kit,
                    part=part,
                    defaults={'quantity': instance.quantity}
                )
                if not created_filter and obj.quantity != instance.quantity:
                    obj.quantity = instance.quantity
                    obj.save()
                logger.info(f"Збережено фільтр '{part}' у наборі ТО для {truck.license_plate}")
    except Exception as e:
        logger.error(f"Помилка авто-збереження набору ТО: {e}")