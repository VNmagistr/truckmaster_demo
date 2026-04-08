"""Хендлер завантаження фото (тільки для адмінів)."""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards import PHOTO_TYPE_LABELS, get_photo_type_keyboard
from bot.queries import check_if_user_is_linked, log_message_to_db, save_order_photo, save_repair_photo

logger = logging.getLogger(__name__)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    is_linked, is_admin, bot_user = await check_if_user_is_linked(user.id)

    if not is_admin:
        await update.message.reply_text("❌ Завантаження фото доступне тільки адміністраторам.")
        return

    photo_type = context.user_data.get('pending_photo_type')
    order_id   = context.user_data.get('photo_order_id')

    if not photo_type or not order_id:
        await update.message.reply_text(
            "ℹ️ Оберіть замовлення і тип фото через кнопку «📷 Фото замовлення»."
        )
        return

    photo     = update.message.photo[-1]
    file_obj  = await context.bot.get_file(photo.file_id)
    photo_bytes = await file_obj.download_as_bytearray()
    label     = PHOTO_TYPE_LABELS.get(photo_type, photo_type)
    filename  = f"{photo_type}_{order_id}_{photo.file_id[-8:]}.jpg"

    try:
        if photo_type == 'repair':
            await save_repair_photo(order_id, bytes(photo_bytes), filename)
        else:
            await save_order_photo(order_id, photo_type, bytes(photo_bytes), filename)

        context.user_data.pop('pending_photo_type', None)
        await update.message.reply_text(
            f"✅ *{label}* збережено!\n\n"
            "Оберіть наступний тип фото або натисніть іншу кнопку меню.",
            parse_mode='Markdown',
            reply_markup=get_photo_type_keyboard(),
        )
    except Exception as e:
        logger.error(f"handle_photo save error: {e}")
        await update.message.reply_text("❌ Помилка при збереженні фото. Спробуйте ще раз.")

    if bot_user:
        await log_message_to_db(
            bot_user,
            f"[photo] {label} → order_id={order_id}",
            "photo saved",
            message_type='photo',
        )
