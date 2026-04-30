import logging
import os

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

from clients.models import Truck

from .models import (
    ServiceWork, MaintenanceKit, MaintenanceKitFilter, ServiceOrder,
    RepairPhoto, TruckMaintenanceIntervals, MaintenanceIntervalsTemplate,
)

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


def _detect_work_type(work, truck=None):
    """Повертає тип роботи: engine_oil | rear_axle | gearbox | auto_gearbox | belts | chains | None."""
    if not work or not _is_maintenance_work(work):
        return None
    name = work.name.lower()
    group = work.work_group.name.lower() if work.work_group else ''
    text = name + ' ' + group

    def matches(text, keywords):
        return any(kw in text for kw in keywords)

    ENGINE_KW       = ('двигун', 'мотор', 'моторн', 'engine')
    GEARBOX_KW      = ('кпп', 'коробк', 'трансміс', 'gearbox')
    AUTO_GEARBOX_KW = ('акпп', 'автоматич')
    AXLE_KW         = ('міст', 'мост', 'axle')
    BELTS_KW        = ('ремін', 'ремн', 'ролик', 'belt')
    CHAINS_KW       = ('ланцюг', 'chain')

    name_only                = work.name.lower()
    is_oil_change            = 'заміна оливи' in text or 'заміна масла' in text
    is_axle                  = matches(text, AXLE_KW)
    # фільтр АКПП: у назві роботи є "фільтр" + "акпп"/"автоматич", але не заміна оливи
    is_auto_gearbox_filter   = ('фільтр' in name_only and matches(text, AUTO_GEARBOX_KW) and not is_oil_change)
    is_auto_gearbox          = matches(text, AUTO_GEARBOX_KW) and not is_auto_gearbox_filter
    is_gearbox               = matches(text, GEARBOX_KW) and not is_auto_gearbox and not is_auto_gearbox_filter

    if is_axle:
        return 'rear_axle'
    if is_auto_gearbox_filter:
        return 'auto_gearbox_filter'
    if is_auto_gearbox:
        return 'auto_gearbox'
    if is_gearbox:
        transmission = getattr(truck, 'transmission_type', None) if truck else None
        if transmission in ('automatic', 'robotic'):
            return 'auto_gearbox'
        return 'gearbox'
    if matches(text, BELTS_KW):
        return 'belts'
    if matches(text, CHAINS_KW):
        return 'chains'
    if matches(text, ENGINE_KW) or is_oil_change:
        return 'engine_oil'
    return 'engine_oil'


@receiver(post_save, sender=ServiceWork)
def auto_add_maintenance_kit(sender, instance, created, **kwargs):
    """
    При створенні роботи типу ТО автоматично додає оливу та запчастини
    з набору ТО для цього авто залежно від типу роботи.
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
    if not truck:
        return

    work_type = _detect_work_type(instance.work, truck=truck)
    if not work_type:
        return

    try:
        kit = MaintenanceKit.objects.get(truck=truck)
    except MaintenanceKit.DoesNotExist:
        logger.info(f"Набір ТО для {truck.license_plate} не знайдено")
        return

    OIL_MAP = {
        'engine_oil':   ('oil',            'oil_quantity'),
        'rear_axle':    ('rear_axle_oil',   'rear_axle_oil_quantity'),
        'gearbox':      ('gearbox_oil',     'gearbox_oil_quantity'),
        'auto_gearbox': ('auto_gearbox_oil','auto_gearbox_oil_quantity'),
    }

    oil_field, qty_field = OIL_MAP.get(work_type, (None, None))
    if oil_field:
        oil_product = getattr(kit, oil_field)
        oil_qty = getattr(kit, qty_field)
        if oil_product and oil_qty:
            oil_part, oil_created = UsedPart.objects.get_or_create(
                service_work=instance,
                part=oil_product,
                defaults={'quantity': int(oil_qty)}
            )
            if oil_created:
                StockService.deduct(oil_part)

    # При заміні оливи АКПП — також списуємо фільтр АКПП з окремого поля
    if work_type == 'auto_gearbox':
        atf_filter = kit.auto_gearbox_filter
        atf_filter_qty = kit.auto_gearbox_filter_quantity
        if atf_filter and atf_filter_qty:
            f_part, f_created = UsedPart.objects.get_or_create(
                service_work=instance,
                part=atf_filter,
                defaults={'quantity': atf_filter_qty}
            )
            if f_created:
                StockService.deduct(f_part)

    # Для двигуна — фільтри both/full/partial; для інших — тільки свій service_type
    if work_type == 'engine_oil':
        filters_qs = kit.filters.filter(service_type__in=('both', 'full', 'partial'))
    else:
        filters_qs = kit.filters.filter(service_type=work_type)

    for kit_filter in filters_qs:
        filter_part, filter_created = UsedPart.objects.get_or_create(
            service_work=instance,
            part=kit_filter.part,
            defaults={'quantity': kit_filter.quantity}
        )
        if filter_created:
            StockService.deduct(filter_part)

    logger.info(f"Автоматично додано набір ТО ({work_type}) для {truck.license_plate}")
    instance.service_order.update_total_cost()


def _update_maintenance_intervals(order):
    """
    При переході наряду в DONE оновлює TruckMaintenanceIntervals:
    встановлює *_last_km = поточний пробіг (або мотогодини, якщо інтервали
    цієї вантажівки ведуться в режимі engine_hours).
    """
    truck = order.truck
    if not truck:
        return

    # Визначаємо режим обліку для цієї вантажівки (якщо запис ще не існує — mileage)
    existing_intervals = getattr(truck, 'maintenance_intervals', None)
    tracking_mode = getattr(existing_intervals, 'tracking_mode', 'mileage') if existing_intervals else 'mileage'

    current_km = order.engine_hours if tracking_mode == 'engine_hours' else order.current_mileage
    if not current_km:
        return

    works = list(order.works.select_related('work__work_group').all())

    ENGINE_KW       = ('двигун', 'мотор', 'моторн', 'engine')
    GEARBOX_KW      = ('кпп', 'коробк', 'трансміс', 'gearbox')
    AUTO_GEARBOX_KW = ('акпп', 'автоматич')
    AXLE_KW         = ('міст', 'мост', 'axle')
    BELTS_KW        = ('ремін', 'ремн', 'ролик', 'belt')
    CHAINS_KW       = ('ланцюг', 'chain')
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

        is_oil_change = 'заміна оливи' in text or 'заміна масла' in text
        is_axle = matches(text, AXLE_KW)
        # фільтр АКПП: у назві роботи є "фільтр" + "акпп"/"автоматич", але не заміна оливи
        is_auto_gearbox_filter = 'фільтр' in name and matches(text, AUTO_GEARBOX_KW) and not is_oil_change
        is_auto_gearbox = matches(text, AUTO_GEARBOX_KW) and not is_auto_gearbox_filter
        is_gearbox = matches(text, GEARBOX_KW) and not is_auto_gearbox and not is_auto_gearbox_filter

        if matches(text, ENGINE_KW) or (is_oil_change and not is_gearbox and not is_auto_gearbox and not is_axle and not is_auto_gearbox_filter):
            fields_to_update['engine_oil_last_km'] = current_km
        if is_gearbox:
            transmission = getattr(truck, 'transmission_type', None)
            if transmission in ('automatic', 'robotic'):
                fields_to_update['auto_gearbox_oil_last_km'] = current_km
            else:
                fields_to_update['gearbox_oil_last_km'] = current_km
        if is_auto_gearbox:
            fields_to_update['auto_gearbox_oil_last_km'] = current_km
        if is_auto_gearbox_filter:
            fields_to_update['auto_gearbox_filter_last_km'] = current_km
        if is_axle:
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


def _find_template_for_truck(truck):
    """Шукає найбільш специфічний еталон інтервалів для цієї вантажівки.

    Пріоритет (зверху вниз):
    1. base_model + euro_standard + transmission_type точно збігаються
    2. base_model + euro_standard (transmission порожній в шаблоні)
    3. base_model + transmission_type (euro порожній)
    4. base_model (обидва порожні)
    """
    if not truck.base_model_id:
        return None

    truck_euro = truck.euro_standard or ''
    truck_trans = truck.transmission_type or ''

    candidates = MaintenanceIntervalsTemplate.objects.filter(base_model_id=truck.base_model_id)

    def _match(euro, trans):
        return candidates.filter(euro_standard=euro, transmission_type=trans).first()

    return (
        _match(truck_euro, truck_trans)
        or _match(truck_euro, '')
        or _match('', truck_trans)
        or _match('', '')
    )


@receiver(post_save, sender=Truck)
def autofill_truck_maintenance_intervals(sender, instance, **kwargs):
    """Після збереження вантажівки заповнює відсутні інтервали ТО з еталона."""
    try:
        template = _find_template_for_truck(instance)
        if not template:
            return

        intervals, created = TruckMaintenanceIntervals.objects.get_or_create(truck=instance)

        update_fields = []
        for field in MaintenanceIntervalsTemplate.INTERVAL_FIELDS:
            if getattr(intervals, field) is None:
                tpl_value = getattr(template, field, None)
                if tpl_value is not None:
                    setattr(intervals, field, tpl_value)
                    update_fields.append(field)

        if created and intervals.tracking_mode != template.tracking_mode:
            intervals.tracking_mode = template.tracking_mode
            update_fields.append('tracking_mode')

        if update_fields:
            intervals.save(update_fields=update_fields)
            logger.info(
                f"Інтервали ТО для {instance.license_plate} автозаповнено з еталона "
                f"{template} ({len(update_fields)} полів)"
            )

        _autofill_maintenance_kit(instance, template)
    except Exception as e:
        logger.error(f"autofill_truck_maintenance_intervals failed for truck {instance.pk}: {e}")


def _autofill_maintenance_kit(truck, template):
    """Заповнює MaintenanceKit + фільтри з еталона (тільки порожні поля)."""
    if not template.oil_id:
        return

    kit, kit_created = MaintenanceKit.objects.get_or_create(
        truck=truck,
        defaults={
            'oil': template.oil,
            'oil_quantity': template.oil_quantity or 0,
        },
    )

    if kit_created:
        for fk_field, qty_field in MaintenanceIntervalsTemplate.OIL_FIELDS:
            val = getattr(template, fk_field, None)
            if val:
                setattr(kit, fk_field, val)
                setattr(kit, qty_field, getattr(template, qty_field))
        if template.auto_gearbox_filter_id:
            kit.auto_gearbox_filter = template.auto_gearbox_filter
            kit.auto_gearbox_filter_quantity = template.auto_gearbox_filter_quantity
        kit.save()
    else:
        update_fields = []
        for fk_field, qty_field in MaintenanceIntervalsTemplate.OIL_FIELDS:
            if getattr(kit, f'{fk_field}_id') is None:
                val = getattr(template, fk_field, None)
                if val:
                    setattr(kit, fk_field, val)
                    setattr(kit, qty_field, getattr(template, qty_field))
                    update_fields.extend([fk_field, qty_field])
        if kit.auto_gearbox_filter_id is None and template.auto_gearbox_filter_id:
            kit.auto_gearbox_filter = template.auto_gearbox_filter
            kit.auto_gearbox_filter_quantity = template.auto_gearbox_filter_quantity
            update_fields.extend(['auto_gearbox_filter', 'auto_gearbox_filter_quantity'])
        if update_fields:
            kit.save(update_fields=update_fields)

    tpl_filters = template.filters.select_related('part').all()
    if tpl_filters and kit_created:
        MaintenanceKitFilter.objects.bulk_create([
            MaintenanceKitFilter(
                maintenance_kit=kit,
                part=f.part,
                quantity=f.quantity,
                change_interval_km=f.change_interval_km,
                service_type=f.service_type,
            )
            for f in tpl_filters
        ])


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
