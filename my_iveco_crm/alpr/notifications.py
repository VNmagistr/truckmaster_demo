from django.utils import timezone
import logging
import os

from core.telegram import send_message as tg_send

logger = logging.getLogger(__name__)


def send_staff_telegram(arrival):
    chat_id = os.environ.get('ALPR_STAFF_CHAT_ID', '')
    if not chat_id:
        logger.warning('ALPR Telegram: ALPR_STAFF_CHAT_ID не задано')
        return

    lines = ['🚛 *Заїзд автомобіля*\n']
    lines.append(f'Номер: `{arrival.license_plate}`')

    if arrival.camera_id:
        lines.append(f'Камера: {arrival.camera_id}')

    if arrival.client:
        lines.append(f'\n👤 Клієнт: *{arrival.client.name}*')
        if arrival.client.phone:
            lines.append(f'Телефон: {arrival.client.phone}')

    if arrival.truck:
        truck = arrival.truck
        lines.append(f'Авто: {truck.specific_model_name} ({truck.license_plate})')

    if arrival.appointment:
        appt = arrival.appointment
        dt_str = timezone.localtime(appt.scheduled_dt).strftime('%d.%m.%Y %H:%M')
        lines.append(f'\n📅 Запис на {dt_str} — {appt.get_service_type_display()}')

    if not arrival.client and not arrival.appointment:
        lines.append('\n⚠️ Автомобіль не знайдено в базі')

    tg_send(chat_id, '\n'.join(lines))
    logger.info(f'ALPR Telegram надіслано для {arrival.license_plate}')
