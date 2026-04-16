import logging
import os

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import ServiceWork, MaintenanceKit, MaintenanceKitFilter, ServiceOrder, RepairPhoto, TruckMaintenanceIntervals

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
    При переході в DONE — закриває нагадування ТО (якщо є робота по заміні оливи).
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

    # Якщо статус змінився на DONE — оновлюємо інтервали ТО
    if (
        previous_status is not None
        and previous_status != ServiceOrder.StatusChoices.DONE
        and instance.status == ServiceOrder.StatusChoices.DONE
    ):
        _update_maintenance_intervals(instance)

    # Якщо статус повернувся з DONE на OPEN/IN_PROGRESS — відновлюємо інтервали
    if (
        previous_status == ServiceOrder.StatusChoices.DONE
        and instance.status in (
            ServiceOrder.StatusChoices.OPEN,
            ServiceOrder.StatusChoices.IN_PROGRESS,
        )
    ):
        _revert_maintenance_intervals(instance)

    # Автоматично встановлюємо дату закриття при переході в CLOSED (якщо не задана вручну)
    if (
        previous_status is not None
        and previous_status != ServiceOrder.StatusChoices.CLOSED
        and instance.status == ServiceOrder.StatusChoices.CLOSED
        and not instance.closed_at
    ):
        ServiceOrder.objects.filter(pk=instance.pk).update(closed_at=timezone.now())
        instance.closed_at = timezone.now()

    # Фінальні статуси — знімок більше не потрібен, видаляємо
    if instance.status in (
        ServiceOrder.StatusChoices.CLOSED,
        ServiceOrder.StatusChoices.CANCELED,
    ) and instance.intervals_snapshot:
        instance.intervals_snapshot = None
        instance.save(update_fields=['intervals_snapshot'])


@receiver([post_save, post_delete], sender=ServiceWork)
def update_order_on_work_change(sender, instance, **kwargs):
    """
    Коли робота створюється, оновлюється або видаляється,
    перераховуємо вартість замовлення.
    Якщо наряд вже у статусі DONE — одразу оновлюємо інтервали ТО,
    бо сигнал зміни статусу вже не спрацює.
    """
    try:
        if instance.service_order_id and instance.service_order:
            order = instance.service_order
            order.update_total_cost()
            if order.status == ServiceOrder.StatusChoices.DONE:
                _update_maintenance_intervals(order)
    except Exception as e:
        logger.debug(f"Не вдалося оновити вартість: {e}")


@receiver(post_save, sender=ServiceWork)
def auto_add_maintenance_kit(sender, instance, created, **kwargs):
    """
    При створенні роботи типу 'ТО' або 'Заміна оливи'
    автоматично додає запчастини з існуючого набору ТО для цього авто.
    Потребує увімкненого модуля 'inventory'.
    """
    from core.registry import is_module_enabled
    from inventory.models import UsedPart
    from inventory.services import StockService

    if not created:
        return

    if not is_module_enabled('inventory'):
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
        oil_part, oil_created = UsedPart.objects.get_or_create(
            service_work=instance,
            part=kit.oil,
            defaults={'quantity': int(kit.oil_quantity)}
        )
        if oil_created:
            StockService.deduct(oil_part)

    for kit_filter in kit.filters.all():
        filter_part, filter_created = UsedPart.objects.get_or_create(
            service_work=instance,
            part=kit_filter.part,
            defaults={'quantity': kit_filter.quantity}
        )
        if filter_created:
            StockService.deduct(filter_part)

    logger.info(f"Автоматично додано набір ТО для {truck.license_plate}")
    instance.service_order.update_total_cost()


def _update_maintenance_intervals(order):
    """
    При переході наряду в DONE оновлює TruckMaintenanceIntervals:
    встановлює *_last_km = поточний пробіг для відповідних типів робіт.
    """
    truck = order.truck
    current_km = order.current_mileage
    if not truck or not current_km:
        return

    works = list(order.works.select_related('work__work_group').all())

    ENGINE_KW  = ('двигун', 'мотор', 'моторн', 'engine')
    GEARBOX_KW = ('кпп', 'акпп', 'коробк', 'трансміс', 'gearbox')
    AXLE_KW    = ('міст', 'мост', 'axle')
    BELTS_KW   = ('ремін', 'ремн', 'ролик', 'belt')
    CHAINS_KW  = ('ланцюг', 'chain')
    INTERVAL_KW = BELTS_KW + CHAINS_KW

    def matches(text, keywords):
        return any(kw in text for kw in keywords)

    def _has_interval_kw(work):
        if not work:
            return False
        text = work.name.lower()
        if work.work_group:
            text += ' ' + work.work_group.name.lower()
        return matches(text, INTERVAL_KW)

    if not any(_is_maintenance_work(sw.work) or _has_interval_kw(sw.work) for sw in works):
        return

    fields_to_update = {}
    for sw in works:
        if not _is_maintenance_work(sw.work) and not _has_interval_kw(sw.work):
            continue
        name = sw.work.name.lower() if sw.work else ''
        group = sw.work.work_group.name.lower() if sw.work and sw.work.work_group else ''
        text = name + ' ' + group

        if matches(text, ENGINE_KW) or 'заміна оливи' in text or 'заміна масла' in text:
            fields_to_update['engine_oil_last_km'] = current_km
        if matches(text, GEARBOX_KW):
            fields_to_update['gearbox_oil_last_km'] = current_km
        if matches(text, AXLE_KW):
            fields_to_update['rear_axle_oil_last_km'] = current_km
        if matches(text, BELTS_KW):
            fields_to_update['belts_last_km'] = current_km
        if matches(text, CHAINS_KW):
            fields_to_update['chains_last_km'] = current_km

    # Загальне ТО без конкретики → оновлюємо оливу двигуна
    if not fields_to_update:
        fields_to_update['engine_oil_last_km'] = current_km

    try:
        intervals, _ = TruckMaintenanceIntervals.objects.get_or_create(truck=truck)

        # Зберігаємо знімок OLD значень перед оновленням
        snapshot = {f: getattr(intervals, f) for f in fields_to_update}
        order.intervals_snapshot = snapshot
        order.save(update_fields=['intervals_snapshot'])

        for field, value in fields_to_update.items():
            setattr(intervals, field, value)
        intervals.save(update_fields=list(fields_to_update.keys()))
        logger.info(
            f"Інтервали ТО оновлено для {truck.license_plate}: "
            f"{fields_to_update} (наряд #{order.order_number})"
        )
    except Exception as e:
        logger.error(f"Помилка оновлення інтервалів ТО: {e}")


def _revert_maintenance_intervals(order):
    """Відновлює *_last_km зі знімку при відкаті статусу з DONE."""
    snapshot = order.intervals_snapshot
    if not snapshot:
        return
    truck = order.truck
    if not truck:
        return
    try:
        intervals, _ = TruckMaintenanceIntervals.objects.get_or_create(truck=truck)
        for field, value in snapshot.items():
            setattr(intervals, field, value)
        intervals.save(update_fields=list(snapshot.keys()))
        order.intervals_snapshot = None
        order.save(update_fields=['intervals_snapshot'])
        logger.info(
            f"Інтервали ТО відновлено для {truck.license_plate} "
            f"(відкат наряду #{order.order_number})"
        )
    except Exception as e:
        logger.error(f"Помилка відновлення інтервалів ТО: {e}")


@receiver(post_save, sender=RepairPhoto)
def notify_client_on_new_photo(sender, instance, created, **kwargs):
    """
    Після додавання фото ремонту надсилає сповіщення клієнту
    через Telegram (якщо є telegram_chat_id) та WhatsApp (якщо є телефон).
    """
    if not created or getattr(instance, '_skip_notification', False):
        return

    client = instance.service_order.client
    if not client:
        return

    order = instance.service_order
    cabinet_url = f"https://ital-truck.com.ua/cabinet/orders/{order.id}"
    base_text = (
        f"📸 Нове фото ремонту\n\n"
        f"Замовлення: №{order.order_number}\n"
        f"Автомобіль: {order.truck.license_plate}\n\n"
        f"Переглянути деталі у особистому кабінеті:\n{cabinet_url}"
    )

    # Перевіряємо індивідуальні фічі клієнта
    try:
        client_features = client.features
    except Exception:
        client_features = None

    if client.telegram_chat_id:
        from core.registry import is_module_enabled
        tg_allowed = (
            is_module_enabled('bot')
            and (client_features is None or client_features.notifications_telegram)
        )
        if tg_allowed:
            from .tasks import send_photo_notification_telegram
            tg_text = base_text.replace("📸 Нове фото ремонту", "📸 *Нове фото ремонту*")
            send_photo_notification_telegram.delay(client.telegram_chat_id, tg_text)

    # --- WhatsApp (перевіряємо фічу клієнта 'notifications_whatsapp') ---
    if client.phone:
        wa_allowed = client_features is None or client_features.notifications_whatsapp
        if wa_allowed:
            try:
                from my_iveco_crm.whatsapp import send_whatsapp_text
                send_whatsapp_text(client.phone, base_text)
            except Exception as e:
                logger.error(f"WhatsApp photo notify error for client {client.id}: {e}")


def auto_save_maintenance_kit(sender, instance, created, **kwargs):
    # Підключається вручну в orders/apps.py після завантаження всіх застосунків
    """
    Коли до роботи ТО додається запчастина — автоматично зберігає/оновлює
    набір ТО для цього автомобіля, щоб використовувати його в майбутніх нарядах.

    Логіка:
    - Олива (category_type in OIL_CATEGORY_TYPES) → створює/оновлює MaintenanceKit,
      плюс додає всі вже наявні фільтри з цієї роботи.
    - Фільтр → якщо kit вже існує, додає/оновлює MaintenanceKitFilter.

    Потребує увімкнених модулів 'inventory' та 'maintenance'.
    """
    from core.registry import is_module_enabled

    if not is_module_enabled('inventory') or not is_module_enabled('maintenance'):
        return

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
