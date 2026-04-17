"""Хендлер inline-callback кнопок."""
import logging
from asgiref.sync import sync_to_async
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.keyboards import (
    get_truck_menu_keyboard, get_maintenance_action_keyboard,
    get_photo_type_keyboard, get_declarations_keyboard, PHOTO_TYPE_LABELS,
)
from bot.queries import (
    get_or_create_bot_user, get_repair_history,
    get_maintenance_history, get_maintenance_status,
)
from bot.handlers.utils import clear_awaiting_states
from bot.nova_poshta import (
    get_client_invoices_with_declarations, client_owns_declaration,
    np_api_track, format_np_status,
)
from clients.models import Truck
from orders.models import ServiceOrder

logger = logging.getLogger(__name__)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    ud   = context.user_data

    if data.startswith("truck_menu_"):
        truck_id = int(data.replace("truck_menu_", ""))
        truck    = await sync_to_async(Truck.objects.get)(id=truck_id)
        await query.edit_message_text(
            f"🚚 *{truck.license_plate}* ({truck.specific_model_name})\n\nОберіть дію:",
            parse_mode='Markdown',
            reply_markup=get_truck_menu_keyboard(truck_id),
        )

    elif data.startswith("truck_history_"):
        truck_id = data.replace("truck_history_", "")
        await query.edit_message_text(await get_repair_history(truck_id))

    elif data.startswith("mileage_truck_"):
        truck_id = int(data.replace("mileage_truck_", ""))
        truck    = await sync_to_async(Truck.objects.get)(id=truck_id)
        clear_awaiting_states(ud)
        ud['awaiting_mileage_truck_id'] = truck_id
        await query.edit_message_text(
            f"🚚 *{truck.license_plate}* ({truck.specific_model_name})\n\n"
            "Введіть поточний пробіг в км (тільки число, наприклад: 185000):",
            parse_mode='Markdown',
        )

    elif data.startswith("maintenance_truck_"):
        truck_id = int(data.replace("maintenance_truck_", ""))
        truck    = await sync_to_async(Truck.objects.get)(id=truck_id)
        await query.edit_message_text(
            f"🚚 *{truck.license_plate}* ({truck.specific_model_name})\n\nОберіть дію:",
            parse_mode='Markdown',
            reply_markup=get_maintenance_action_keyboard(truck_id),
        )

    elif data.startswith("maint_history_"):
        truck_id = int(data.replace("maint_history_", ""))
        await query.edit_message_text(await get_maintenance_history(truck_id), parse_mode='Markdown')

    elif data.startswith("maint_remaining_"):
        truck_id = int(data.replace("maint_remaining_", ""))
        truck    = await sync_to_async(Truck.objects.get)(id=truck_id)
        clear_awaiting_states(ud)
        ud['awaiting_maintenance_mileage_truck_id'] = truck_id
        await query.edit_message_text(
            f"🚚 *{truck.license_plate}* ({truck.specific_model_name})\n\n"
            "Введіть поточний пробіг (тільки число, наприклад: 185000):",
            parse_mode='Markdown',
        )

    elif data.startswith("photo_order_"):
        order_id = int(data.replace("photo_order_", ""))
        order    = await sync_to_async(
            lambda: ServiceOrder.objects.select_related('truck').get(id=order_id)
        )()
        plate = order.truck.license_plate if order.truck else '—'
        ud['photo_order_id']      = order_id
        ud['awaiting_photo_order'] = False
        await query.edit_message_text(
            f"✅ Замовлення *{order.order_number}* ({plate})\n\nОберіть тип фото:",
            parse_mode='Markdown',
            reply_markup=get_photo_type_keyboard(),
        )

    elif data.startswith("photo_type_"):
        photo_type = data.replace("photo_type_", "")
        order_id   = ud.get('photo_order_id')
        if not order_id:
            await query.edit_message_text("❌ Сесія завершена. Почніть знову через «📷 Фото замовлення».")
            return
        ud['pending_photo_type'] = photo_type
        label = PHOTO_TYPE_LABELS.get(photo_type, photo_type)
        await query.edit_message_text(f"📸 Тип: *{label}*\n\nНадішліть фото:", parse_mode='Markdown')

    elif data.startswith("np_track_"):
        declaration = data.replace("np_track_", "")
        bot_user    = await get_or_create_bot_user(query.from_user)
        if not await client_owns_declaration(bot_user, declaration):
            await query.answer("⛔ Декларація не належить вашому акаунту.", show_alert=True)
            return
        await query.edit_message_text(f"⏳ Отримую статус для ТТН {declaration}…")
        np_data     = await np_api_track(declaration)
        status_text = format_np_status(np_data)
        await query.edit_message_text(
            f"ТТН: `{declaration}`\n\n{status_text}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ До списку відправок", callback_data="np_back"),
            ]]),
        )

    elif data == "np_back":
        bot_user = await get_or_create_bot_user(query.from_user)
        invoices = await get_client_invoices_with_declarations(bot_user)
        if not invoices:
            await query.edit_message_text("📭 Відправлень з номером декларації не знайдено.")
        else:
            await query.edit_message_text(
                f"📦 Ваші відправки ({len(invoices)}):\nОберіть декларацію для перевірки статусу:",
                reply_markup=get_declarations_keyboard(invoices),
            )

    elif data == "np_close":
        await query.edit_message_text("✅ Закрито.")

    elif data == "photo_cancel":
        ud.pop('photo_order_id', None)
        ud.pop('pending_photo_type', None)
        ud.pop('awaiting_photo_order', None)
        await query.edit_message_text("❌ Завантаження фото скасовано.")
