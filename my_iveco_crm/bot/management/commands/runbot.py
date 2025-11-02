import os
import logging
import asyncio
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton # 1. Імпортуємо кнопки
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from orders.models import ServiceOrder
from bot.models import BotMessageLog
from asgiref.sync import sync_to_async

# ... (код логування та BOT_TOKEN) ...

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
logger = logging.getLogger(__name__)

# --- Функція збереження в БД ---
@sync_to_async
def log_message(chat_id, user_name, message_text, bot_response, phone_number=None):
    """
    Асинхронно зберігає повідомлення та відповідь бота у базу даних.
    """
    try:
        # Спочатку шукаємо останній лог, щоб отримати номер телефону, якщо він вже є
        if not phone_number:
            last_log = await BotMessageLog.objects.filter(chat_id=chat_id).order_by('-created_at').first()
            if last_log and last_log.phone_number:
                phone_number = last_log.phone_number

        BotMessageLog.objects.create(
            chat_id=chat_id,
            user_name=user_name,
            phone_number=phone_number, # <-- Зберігаємо номер
            message_text=message_text,
            bot_response=bot_response
        )
        logger.info(f"Лог збережено для {chat_id}")
    except Exception as e:
        logger.error(f"Не вдалося зберегти лог для {chat_id}: {e}")

# --- Обробники ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Надсилає вітальне повідомлення та запитує номер телефону."""
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    message_text = update.message.text

    # Створюємо кнопку для запиту контакту
    contact_keyboard = KeyboardButton(text="Надати номер телефону", request_contact=True)
    custom_keyboard = [[contact_keyboard]]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True, one_time_keyboard=True)

    reply_text = (
        f'Вітаю, {user_name}!\n\n'
        'Для кращої ідентифікації у системі, будь ласка, поділіться вашим номером телефону, натиснувши кнопку нижче.\n\n'
    )

    await update.message.reply_text(reply_text, reply_markup=reply_markup)

    await log_message(chat_id, user_name, message_text, reply_text)

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє отриманий контакт (номер телефону)."""
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    phone_number = update.message.contact.phone_number

    reply_text = f"Дякую, {user_name}! Ваш номер {phone_number} збережено."

    # Відправляємо відповідь вже без кнопки
    await update.message.reply_text(reply_text, reply_markup=None) 

    await log_message(chat_id, user_name, f"[Надано контакт: {phone_number}]", reply_text, phone_number)

async def check_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє текстове повідомлення та викликає синхронну функцію БД."""
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    original_text = update.message.text

    order_number = re.sub(r'\D', '', original_text)

    if not order_number:
        reply_message = f"'{original_text}' - це наразі невідома мені команда. Спробуйте ще раз пізніше"
        await update.message.reply_text(reply_message)
        await log_message(chat_id, user_name, original_text, reply_message)
        return

    reply_message = await get_order_from_db(order_number)
    await update.message.reply_text(reply_message)

    await log_message(chat_id, user_name, original_text, reply_message)

# ... (функція get_order_from_db залишається БЕЗ ЗМІН) ...
@sync_to_async
def get_order_from_db(order_number):
    # ...
    # ... код всередині без змін ...
    # ...
    try:
        order = ServiceOrder.objects.select_related('client', 'truck').get(order_number=order_number)

        reply = (
            f"Замовлення №{order.order_number}\n"
            f"Статус: {order.get_status_display()}\n"
            f"Клієнт: {order.client.name}\n"
            f"Вантажівка: {order.truck.license_plate}"
        )
        return reply

    except ServiceOrder.DoesNotExist:
        return f"Замовлення з номером {order_number} не знайдено. Будь ласка, перевірте номер."
    except Exception as e:
        logger.error(f"Помилка під час запиту до БД: {e}")
        return "Виникла помилка на сервері. Ми вже працюємо над цим."

# --- Клас команди Django ---
class Command(BaseCommand):
    help = 'Запускає Telegram бота'

    def handle(self, *args, **options):
        if not BOT_TOKEN:
            logger.error("ПОМИЛКА: Змінна оточення TELEGRAM_BOT_TOKEN не встановлена!")
            return

        self.stdout.write(self.style.SUCCESS('Бот запускається...'))

        application = Application.builder().token(BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        # 3. Додаємо обробник для контактів
        application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_order_status))

        try:
            asyncio.run(application.run_polling())
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Бот зупинено.'))