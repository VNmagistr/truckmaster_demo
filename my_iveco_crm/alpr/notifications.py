import asyncio
import logging
import os

logger = logging.getLogger(__name__)


def send_staff_telegram(arrival):
    """
    Надсилає Telegram-сповіщення в чат персоналу про заїзд автомобіля.
    ALPR_STAFF_CHAT_ID — ID групи/каналу де сидять менеджери/механіки.
    """
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('ALPR_STAFF_CHAT_ID', '')
    if not bot_token or not chat_id:
        logger.warning("ALPR Telegram: TELEGRAM_BOT_TOKEN або ALPR_STAFF_CHAT_ID не задані")
        return

    lines = [f"🚛 *Заїзд автомобіля*\n"]
    lines.append(f"Номер: `{arrival.license_plate}`")

    if arrival.camera_id:
        lines.append(f"Камера: {arrival.camera_id}")

    if arrival.client:
        lines.append(f"\n👤 Клієнт: *{arrival.client.name}*")
        if arrival.client.phone:
            lines.append(f"Телефон: {arrival.client.phone}")

    if arrival.truck:
        truck = arrival.truck
        lines.append(f"Авто: {truck.specific_model_name} ({truck.license_plate})")

    if arrival.appointment:
        appt = arrival.appointment
        dt_str = appt.scheduled_dt.strftime('%d.%m.%Y %H:%M')
        lines.append(f"\n📅 Запис на {dt_str} — {appt.get_service_type_display()}")

    if not arrival.client and not arrival.appointment:
        lines.append("\n⚠️ Автомобіль не знайдено в базі")

    text = "\n".join(lines)

    try:
        from telegram import Bot
        bot = Bot(token=bot_token)
        asyncio.run(bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
        ))
        logger.info(f"ALPR Telegram надіслано для {arrival.license_plate}")
    except Exception as e:
        logger.error(f"ALPR Telegram помилка: {e}")
