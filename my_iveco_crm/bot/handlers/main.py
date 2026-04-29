"""Основні хендлери: start, contact, my_cars, handle_text."""
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from bot.keyboards import (
    MAIN_REPLY_MARKUP, ADMIN_REPLY_MARKUP,
    get_photo_type_keyboard, get_order_selection_keyboard,
    get_declarations_keyboard,
)
from bot.handlers.utils import clear_awaiting_states
from bot.queries import (
    get_or_create_bot_user, check_if_user_is_linked, is_email_verified_for_bot,
    link_bot_user_by_phone, log_message_to_db, get_my_cars_with_keyboard,
    find_truck_by_plate, find_client_by_name, get_order_status,
    get_orders_for_photo, save_mileage_report, get_client_reminders,
    get_maintenance_status,
)
from bot.nova_poshta import get_client_invoices_with_declarations

logger = logging.getLogger(__name__)

_EMAIL_BLOCK_MSG = (
    "🔒 Для використання бота необхідно підтвердити email адресу.\n\n"
    "Перейдіть до особистого кабінету: https://ital-truck.com.ua/cabinet\n"
    "та підтвердіть email, або запросіть новий лист підтвердження."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user     = update.message.from_user
    bot_user = await get_or_create_bot_user(user)
    is_linked, is_admin, _ = await check_if_user_is_linked(user.id)

    if is_linked:
        if not await is_email_verified_for_bot(bot_user):
            bot_reply = _EMAIL_BLOCK_MSG
        else:
            markup    = ADMIN_REPLY_MARKUP if is_admin else MAIN_REPLY_MARKUP
            bot_reply = f"Вітаю, {bot_user.first_name}!"
            await update.message.reply_text(bot_reply, reply_markup=markup)
            if bot_user:
                await log_message_to_db(bot_user, '/start', bot_reply, message_type='command')
            return
    else:
        btn       = KeyboardButton("Надати номер телефону", request_contact=True)
        bot_reply = "Я вас не знаю. Надайте номер:"
        await update.message.reply_text(
            bot_reply,
            reply_markup=ReplyKeyboardMarkup([[btn]], resize_keyboard=True),
        )
        if bot_user:
            await log_message_to_db(bot_user, '/start', bot_reply, message_type='command')
        return

    await update.message.reply_text(bot_reply)
    if bot_user:
        await log_message_to_db(bot_user, '/start', bot_reply, message_type='command')


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user      = update.message.from_user
    bot_user  = await get_or_create_bot_user(user)
    bot_reply = await link_bot_user_by_phone(bot_user, update.message.contact.phone_number)

    is_linked, is_admin, _ = await check_if_user_is_linked(user.id)
    markup = ADMIN_REPLY_MARKUP if is_admin else (MAIN_REPLY_MARKUP if is_linked else None)

    await update.message.reply_text(bot_reply, reply_markup=markup)
    if bot_user:
        await log_message_to_db(
            bot_user,
            f"[контакт] {update.message.contact.phone_number}",
            bot_reply,
            message_type='contact',
        )


async def my_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user     = update.message.from_user
    bot_user = await get_or_create_bot_user(user)
    res      = await get_my_cars_with_keyboard(bot_user)
    await update.message.reply_text(res["reply_text"], reply_markup=res["keyboard"])
    if bot_user:
        await log_message_to_db(bot_user, update.message.text, res["reply_text"])


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text     = update.message.text
    user     = update.message.from_user
    bot_user = await get_or_create_bot_user(user)
    bot_reply = "Оберіть дію з меню."

    if bot_user and bot_user.client_id and not await is_email_verified_for_bot(bot_user):
        await update.message.reply_text(_EMAIL_BLOCK_MSG)
        if bot_user:
            await log_message_to_db(bot_user, text, _EMAIL_BLOCK_MSG)
        return

    ud = context.user_data

    if ud.get('awaiting_maintenance_mileage_truck_id') and text.strip().isdigit():
        truck_id  = ud.pop('awaiting_maintenance_mileage_truck_id')
        bot_reply = await get_maintenance_status(truck_id, int(text.strip()))
        await update.message.reply_text(bot_reply, parse_mode='Markdown')

    elif ud.get('awaiting_mileage_truck_id') and text.strip().isdigit():
        truck_id            = ud.pop('awaiting_mileage_truck_id')
        _, bot_reply        = await save_mileage_report(bot_user, truck_id, int(text.strip()))
        await update.message.reply_text(bot_reply, parse_mode='Markdown')

    elif ud.get('awaiting_truck'):
        bot_reply = await find_truck_by_plate(text, bot_user)
        await update.message.reply_text(bot_reply)
        ud['awaiting_truck'] = False

    elif ud.get('awaiting_client'):
        bot_reply = await find_client_by_name(text)
        await update.message.reply_text(bot_reply)
        ud['awaiting_client'] = False

    elif ud.get('awaiting_order'):
        bot_reply = await get_order_status(text)
        await update.message.reply_text(bot_reply, parse_mode='Markdown')
        ud['awaiting_order'] = False

    elif ud.get('awaiting_photo_order'):
        orders = await get_orders_for_photo(text)
        if not orders:
            bot_reply = f"❌ Замовлення '{text}' не знайдено. Спробуйте ще раз."
            await update.message.reply_text(bot_reply)
        elif len(orders) == 1:
            order = orders[0]
            plate = order.truck.license_plate if order.truck else '—'
            ud['photo_order_id']     = order.id
            ud['awaiting_photo_order'] = False
            bot_reply = f"✅ Замовлення *{order.order_number}* ({plate})\n\nОберіть тип фото:"
            await update.message.reply_text(bot_reply, parse_mode='Markdown',
                                            reply_markup=get_photo_type_keyboard())
        else:
            bot_reply = f"Знайдено {len(orders)} замовлень. Оберіть потрібне:"
            await update.message.reply_text(bot_reply,
                                            reply_markup=get_order_selection_keyboard(orders))

    elif "Нагадування" in text:
        reminders = await get_client_reminders(bot_user)
        if not reminders:
            bot_reply = "✅ Активних нагадувань немає."
            await update.message.reply_text(bot_reply)
        else:
            lines = ["🔔 *Нагадування про обслуговування:*\n"]
            for r in reminders:
                icon = {"pending": "⏳", "notified": "📬", "overdue": "🚨"}.get(r['status'], "🔔")
                lines.append(f"{icon} *{r['title']}*")
                lines.append(f"   🚚 {r['plate']}")
                if r['km_left'] is not None:
                    if r['km_left'] > 0:
                        lines.append(f"   📏 Залишилось: ~{r['km_left']:,} км".replace(",", " "))
                    else:
                        lines.append(f"   ⚠️ Пробіг перевищено на {abs(r['km_left']):,} км!".replace(",", " "))
                if r['days_left'] is not None:
                    if r['days_left'] > 0:
                        lines.append(f"   📅 Залишилось: {r['days_left']} днів")
                    elif r['days_left'] == 0:
                        lines.append(f"   📅 Термін сьогодні!")
                    else:
                        lines.append(f"   📅 Прострочено на {abs(r['days_left'])} днів!")
                lines.append("")
            bot_reply = "\n".join(lines)
            await update.message.reply_text(bot_reply, parse_mode='Markdown')

    elif "Мої відправки" in text:
        invoices = await get_client_invoices_with_declarations(bot_user)
        if not invoices:
            bot_reply = "📭 Відправлень з номером декларації Нової Пошти не знайдено."
            await update.message.reply_text(bot_reply)
        else:
            bot_reply = f"📦 Ваші відправки ({len(invoices)}):\nОберіть декларацію для перевірки статусу:"
            await update.message.reply_text(bot_reply,
                                            reply_markup=get_declarations_keyboard(invoices))

    elif "Перевірити статус замовлення" in text:
        bot_reply = "Введіть номер замовлення:"
        clear_awaiting_states(ud)
        ud['awaiting_order'] = True
        await update.message.reply_text(bot_reply)

    else:
        await update.message.reply_text(bot_reply)

    if bot_user:
        await log_message_to_db(bot_user, text, bot_reply)
