"""
DB-функції бота. Всі синхронні функції обгорнуті в @sync_to_async,
тому їх можна await-ити з async-хендлерів без блокування event loop.
"""
import logging
from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from django.db.models import Q
from django.utils import timezone

from clients.models import Client, Truck
from bot.models import BotUser, BotMessageLog, UnknownPlateSearch
from orders.models import ServiceOrder, RepairPhoto

logger = logging.getLogger(__name__)


# ── Користувачі ──────────────────────────────────────────────────────────────

@sync_to_async
def get_or_create_bot_user(telegram_user):
    try:
        bot_user, created = BotUser.objects.get_or_create(
            telegram_id=telegram_user.id,
            defaults={
                'username':      telegram_user.username or '',
                'first_name':    telegram_user.first_name or '',
                'last_name':     telegram_user.last_name or '',
                'language_code': telegram_user.language_code or 'uk',
                'role':          'guest',
                'is_active':     True,
            }
        )
        if not created:
            updated = False
            if bot_user.username != (telegram_user.username or ''):
                bot_user.username = telegram_user.username or ''
                updated = True
            if bot_user.first_name != (telegram_user.first_name or ''):
                bot_user.first_name = telegram_user.first_name or ''
                updated = True
            if updated:
                bot_user.save()
        return bot_user
    except Exception as e:
        logger.error(f"get_or_create_bot_user error: {e}")
        return None


@sync_to_async
def check_if_user_is_linked(telegram_id):
    try:
        bot_user = BotUser.objects.select_related('client').get(telegram_id=telegram_id)
        return bot_user.client is not None, bot_user.role == 'admin', bot_user
    except BotUser.DoesNotExist:
        return False, False, None


@sync_to_async
def is_email_verified_for_bot(bot_user):
    """
    Блокує тільки клієнтів із кабінетним акаунтом (user != None),
    email яких не верифіковано. Клієнти без кабінету — без обмежень.
    """
    if not bot_user or not bot_user.client_id:
        return True
    try:
        client = Client.objects.get(id=bot_user.client_id)
        if client.user_id and not client.email_verified:
            return False
        return True
    except Exception:
        return True


@sync_to_async
def link_bot_user_by_phone(bot_user, phone_number):
    try:
        clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')[-9:]
        client = Client.objects.filter(phone__contains=clean_phone).first()

        if not client:
            return (
                f"Дякую, {bot_user.first_name}! На жаль, я не знайшов КЛІЄНТА з номером "
                f"{phone_number}. Якщо ви механік — цей бот не для вас. "
                "Якщо клієнт — зверніться до менеджера."
            )

        bot_user.client = client
        bot_user.phone_number = phone_number
        bot_user.role = 'admin' if client.is_admin else ('owner' if client.truck_set.exists() else 'guest')
        bot_user.assigned_trucks.set(client.truck_set.all())
        bot_user.save()
        return f"Вітаю! Ваш профіль клієнта '{client.name}' успішно прив'язано."
    except Exception as e:
        logger.error(f"link_bot_user_by_phone error: {e}")
        return "Виникла помилка. Спробуйте пізніше."


@sync_to_async
def log_message_to_db(bot_user, message_text, bot_response, message_type='text', is_incoming=True):
    try:
        BotMessageLog.objects.create(
            bot_user=bot_user,
            message_type=message_type,
            is_incoming=is_incoming,
            message_text=message_text,
            bot_response=bot_response,
            is_processed=True,
        )
    except Exception as e:
        logger.error(f"log_message_to_db error: {e}")


# ── Автомобілі ───────────────────────────────────────────────────────────────

@sync_to_async
def get_my_cars_with_keyboard(bot_user):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    if not bot_user.client:
        return {"reply_text": "Ви не авторизовані як клієнт.", "keyboard": None}

    # Водій бачить лише закріплені за ним авто; власник — усі авто свого клієнта.
    if bot_user.role == 'driver':
        trucks = bot_user.assigned_trucks.filter(marked_for_deletion=False)
    else:
        trucks = Truck.objects.filter(
            client=bot_user.client,
            marked_for_deletion=False,
        )
    trucks = trucks.order_by('license_plate')

    if not trucks.exists():
        return {"reply_text": "За вами не закріплено авто.", "keyboard": None}

    keyboard = [
        [InlineKeyboardButton(
            f"🚚 {t.license_plate} ({t.specific_model_name})",
            callback_data=f"truck_menu_{t.id}",
        )]
        for t in trucks
    ]
    return {"reply_text": "Ваші автомобілі:", "keyboard": InlineKeyboardMarkup(keyboard)}


@sync_to_async
def find_truck_by_plate(plate, bot_user=None):
    clean = plate.strip().upper().replace(' ', '')
    if not clean:
        return "Не знайдено."
    trucks = Truck.objects.filter(license_plate__icontains=clean).select_related('client')
    if not trucks:
        try:
            obj, created = UnknownPlateSearch.objects.get_or_create(
                plate=clean,
                defaults={'last_searched_by': bot_user},
            )
            if not created:
                obj.search_count = (obj.search_count or 0) + 1
                if bot_user:
                    obj.last_searched_by = bot_user
                obj.save(update_fields=['search_count', 'last_searched_by', 'last_searched_at'])
        except Exception as e:
            logger.error(f"log unknown plate failed: {e}")
        return "Не знайдено."
    return ''.join(
        f"🚚 {t.license_plate} ({t.specific_model_name})\n"
        f"Власник: {t.client.name if t.client else '-'}\n\n"
        for t in trucks[:5]
    )


@sync_to_async
def get_repair_history(truck_id):
    try:
        truck = Truck.objects.get(id=truck_id)
        orders = ServiceOrder.objects.filter(truck=truck).order_by('-created_at')[:5]
        if not orders:
            return "Історії немає."
        reply = f"Історія {truck.license_plate}:\n"
        for o in orders:
            reply += f"🔹 {timezone.localtime(o.created_at).strftime('%d.%m.%y')} - {o.get_status_display()}\n"
        return reply
    except Exception:
        return "Помилка."


# ── Замовлення ───────────────────────────────────────────────────────────────

@sync_to_async
def get_order_status(order_number):
    try:
        order = ServiceOrder.objects.select_related('client', 'truck').get(
            order_number=order_number.strip()
        )
        text = f"📝 *Замовлення №{order.order_number}*\n\n"
        text += f"📊 Статус: *{order.get_status_display()}*\n"
        text += f"📅 Дата: {timezone.localtime(order.created_at).strftime('%d.%m.%Y')}\n"
        if order.truck:
            info = order.truck.license_plate
            if order.truck.specific_model_name:
                info += f" ({order.truck.specific_model_name})"
            text += f"🚚 Авто: {info}\n"
        if order.client:
            text += f"👤 Клієнт: {order.client.name}\n"
        if order.problem_description:
            text += f"📋 Опис: {order.problem_description[:200]}\n"
        if order.total_cost:
            text += f"💰 Вартість: {order.total_cost} грн\n"
        return text
    except ServiceOrder.DoesNotExist:
        return f"❌ Замовлення #{order_number} не знайдено."


@sync_to_async
def get_orders_for_photo(query):
    query = query.strip()
    exact = ServiceOrder.objects.filter(order_number=query).select_related('truck')
    if exact.exists():
        return list(exact[:1])
    return list(
        ServiceOrder.objects.filter(order_number__endswith=query)
        .select_related('truck')
        .order_by('-created_at')[:10]
    )


# ── Регламентні роботи ───────────────────────────────────────────────────────

@sync_to_async
def get_maintenance_history(truck_id):
    from orders.models import TruckMaintenanceIntervals
    try:
        truck = Truck.objects.get(id=truck_id)
    except Truck.DoesNotExist:
        return "❌ Вантажівку не знайдено."

    try:
        intervals = TruckMaintenanceIntervals.objects.get(truck=truck)
    except TruckMaintenanceIntervals.DoesNotExist:
        intervals = None

    transmission = getattr(truck, 'transmission_type', None)
    if transmission == 'manual':
        gearbox_items = [('gearbox_oil_last_km', '⚙️ Олива КПП')]
    elif transmission == 'automatic':
        gearbox_items = [
            ('auto_gearbox_oil_last_km',    '⚙️ Олива АКПП'),
            ('auto_gearbox_filter_last_km', '🔘 Фільтр АКПП'),
        ]
    elif transmission == 'robotic':
        gearbox_items = [
            ('auto_gearbox_oil_last_km',    '⚙️ Олива роботизованої КПП'),
            ('auto_gearbox_filter_last_km', '🔘 Фільтр роботизованої КПП'),
        ]
    else:
        gearbox_items = [
            ('gearbox_oil_last_km', '⚙️ Олива КПП'),
            ('auto_gearbox_oil_last_km', '⚙️ Олива АКПП'),
        ]
    ITEMS = [
        ('engine_oil_last_km',    '🛢 Олива двигуна'),
        *gearbox_items,
        ('rear_axle_oil_last_km', '🔩 Олива заднього моста'),
        ('belts_last_km',         '🔗 Ремені/ролики'),
        ('chains_last_km',        '⛓ Ланцюги'),
    ]
    lines = [
        f"🚚 *{truck.license_plate}* ({truck.specific_model_name})",
        "",
        "📅 *Коли виконувались регламентні роботи:*\n",
    ]
    for field, label in ITEMS:
        last_km = getattr(intervals, field, None) if intervals else None
        order = (
            ServiceOrder.objects
            .filter(truck=truck, intervals_snapshot__has_key=field)
            .order_by('-updated_at')
            .first()
        )
        lines.append(label)
        if order:
            date_str = timezone.localtime(order.updated_at).strftime('%d.%m.%Y')
            km_str = f"{last_km:,}".replace(",", " ") if last_km else "—"
            lines.append(f"   📅 {date_str}   •   📏 {km_str} км")
            lines.append(f"   _(Наряд {order.order_number})_\n")
        elif last_km:
            km_str = f"{last_km:,}".replace(",", " ")
            lines.append(f"   📏 {km_str} км _(дата не збережена)_\n")
        else:
            lines.append("   ❓ Даних немає\n")
    return "\n".join(lines)


@sync_to_async
def get_maintenance_status(truck_id, mileage):
    from orders.models import TruckMaintenanceIntervals
    try:
        truck = Truck.objects.get(id=truck_id)
    except Truck.DoesNotExist:
        return "❌ Вантажівку не знайдено."

    try:
        intervals = TruckMaintenanceIntervals.objects.get(truck=truck)
    except TruckMaintenanceIntervals.DoesNotExist:
        return (
            f"🚚 *{truck.license_plate}* ({truck.specific_model_name})\n\n"
            "ℹ️ Для цього автомобіля ще не налаштовано інтервали регламентних робіт.\n"
            "Зверніться до менеджера сервісного центру."
        )

    transmission = getattr(truck, 'transmission_type', None)
    if transmission == 'manual':
        gearbox_items_s = [('gearbox_oil', '⚙️ Олива КПП')]
    elif transmission == 'automatic':
        gearbox_items_s = [
            ('auto_gearbox_oil',    '⚙️ Олива АКПП'),
            ('auto_gearbox_filter', '🔘 Фільтр АКПП'),
        ]
    elif transmission == 'robotic':
        gearbox_items_s = [
            ('auto_gearbox_oil',    '⚙️ Олива роботизованої КПП'),
            ('auto_gearbox_filter', '🔘 Фільтр роботизованої КПП'),
        ]
    else:
        gearbox_items_s = [
            ('gearbox_oil', '⚙️ Олива КПП'),
            ('auto_gearbox_oil', '⚙️ Олива АКПП'),
        ]
    ITEMS = [
        ('engine_oil',    '🛢 Олива двигуна'),
        *gearbox_items_s,
        ('rear_axle_oil', '🔩 Олива заднього моста'),
        ('belts',         '🔗 Ремені/ролики'),
        ('chains',        '⛓ Ланцюги'),
    ]
    fmt_mileage = f"{mileage:,}".replace(",", " ")
    lines = [
        f"🚚 *{truck.license_plate}* ({truck.specific_model_name})",
        f"📏 Поточний пробіг: *{fmt_mileage} км*\n",
        "🔧 *Стан регламентних робіт:*\n",
    ]
    has_data = False
    for key, label in ITEMS:
        interval = getattr(intervals, f"{key}_interval")
        last_km  = getattr(intervals, f"{key}_last_km")
        if interval is None or last_km is None:
            lines.append(f"{label}\n   ❓ Дані відсутні\n")
            continue
        has_data = True
        next_km   = last_km + interval
        remaining = next_km - mileage
        fmt_last = f"{last_km:,}".replace(",", " ")
        fmt_next = f"{next_km:,}".replace(",", " ")
        if remaining > 0:
            fmt_rem = f"{remaining:,}".replace(",", " ")
            icon = "✅" if remaining > 0.2 * interval else "⚠️"
            lines.append(
                f"{label}\n"
                f"   {icon} Залишилось: *{fmt_rem} км*\n"
                f"   _(остання: {fmt_last} км → наступна: {fmt_next} км)_\n"
            )
        else:
            fmt_over = f"{abs(remaining):,}".replace(",", " ")
            lines.append(
                f"{label}\n"
                f"   🚨 Прострочено на *{fmt_over} км*!\n"
                f"   _(мало бути: {fmt_next} км)_\n"
            )
    if not has_data:
        lines.append("ℹ️ Інтервали не налаштовано. Зверніться до менеджера.")
    return "\n".join(lines)


# ── Пробіг ───────────────────────────────────────────────────────────────────

@sync_to_async
def save_mileage_report(bot_user, truck_id, mileage):
    from bot.models import MileageReport
    truck = Truck.objects.get(id=truck_id)
    MileageReport.objects.create(bot_user=bot_user, truck=truck, mileage=mileage)
    formatted = f"{mileage:,}".replace(",", " ")
    reply = (
        f"✅ Пробіг *{formatted} км* для *{truck.license_plate}* збережено. Дякуємо!\n\n"
        "Ми повідомимо вас коли підійде час технічного обслуговування."
    )
    return truck, reply


# ── Нагадування ──────────────────────────────────────────────────────────────

@sync_to_async
def get_client_reminders(bot_user):
    from maintenance.models import ServiceReminder
    if not bot_user.client:
        return []
    # Власник бачить нагадування для всіх авто свого клієнта,
    # водій — лише для закріплених за ним.
    if bot_user.role == 'driver':
        trucks = list(bot_user.assigned_trucks.filter(marked_for_deletion=False))
    else:
        trucks = list(Truck.objects.filter(
            client=bot_user.client,
            marked_for_deletion=False,
        ))
    if not trucks:
        return []
    reminders = list(
        ServiceReminder.objects.filter(
            truck__in=trucks,
            status__in=['pending', 'notified', 'overdue'],
        ).select_related('truck').order_by('status', 'target_mileage', 'target_date')
    )
    today = timezone.now().date()
    result = []
    for r in reminders:
        current_mileage = r.truck.get_latest_mileage()
        result.append({
            'title':           r.title,
            'plate':           r.truck.license_plate,
            'status':          r.status,
            'km_left':         (r.target_mileage - current_mileage) if r.target_mileage and current_mileage else None,
            'days_left':       (r.target_date - today).days if r.target_date else None,
            'target_mileage':  r.target_mileage,
            'current_mileage': current_mileage,
        })
    return result


# ── Адмін ────────────────────────────────────────────────────────────────────

@sync_to_async
def get_all_trucks():
    trucks = Truck.objects.select_related('client').all()[:10]
    if not trucks:
        return "Немає даних."
    reply = "📋 Всі авто (топ 10):\n"
    for t in trucks:
        reply += f"🚚 {t.license_plate} ({t.specific_model_name}) - {t.client.name if t.client else '---'}\n"
    return reply


@sync_to_async
def get_all_orders():
    orders = ServiceOrder.objects.select_related('client', 'truck').order_by('-created_at')[:10]
    if not orders:
        return "Немає замовлень."
    reply = "📋 Останні замовлення:\n"
    for o in orders:
        reply += f"🧾 №{o.order_number} | {o.truck.license_plate if o.truck else '-'} | {o.get_status_display()}\n"
    return reply


@sync_to_async
def get_statistics():
    from django.db.models import Count
    from clients.models import Client, Truck
    return (
        f"📊 Статистика:\n"
        f"Клієнтів: {Client.objects.count()}\n"
        f"Авто: {Truck.objects.count()}\n"
        f"Замовлень: {ServiceOrder.objects.count()}"
    )


@sync_to_async
def find_client_by_name(name):
    clients = Client.objects.filter(name__icontains=name.strip())[:5]
    if not clients:
        return "Не знайдено."
    return ''.join(f"👤 {c.name} ({c.phone or '-'})\n" for c in clients)


# ── Фото ─────────────────────────────────────────────────────────────────────

@sync_to_async
def save_order_photo(order_id, photo_type, photo_bytes, filename):
    order = ServiceOrder.objects.get(id=order_id)
    content = ContentFile(photo_bytes, name=filename)
    field_map = {'car': 'car_photo', 'odometer': 'odometer_photo', 'dashboard': 'dashboard_photo'}
    getattr(order, field_map[photo_type]).save(filename, content, save=True)


@sync_to_async
def save_repair_photo(order_id, photo_bytes, filename):
    order = ServiceOrder.objects.get(id=order_id)
    repair_photo = RepairPhoto(service_order=order)
    repair_photo.image.save(filename, ContentFile(photo_bytes, name=filename), save=True)
