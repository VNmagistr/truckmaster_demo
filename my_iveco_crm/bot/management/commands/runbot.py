import os
import logging
import asyncio
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from orders.models import ServiceOrder
from bot.models import BotMessageLog  # 1. Імпортуємо нашу нову модель
from asgiref.sync import sync_to_async

# Налаштовуємо логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Налаштування ---
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# --- Нова функція для запису в БД ---
@sync_to_async
def log_message(chat_id, user_name, message_text, bot_response):
    """
    Асинхронно зберігає повідомлення та відповідь бота у базу даних.
    """
    try:
        BotMessageLog.objects.create(
            chat_id=chat_id,
            user_name=user_name,
            message_text=message_text,
            bot_response=bot_response
        )
        logger.info(f"Лог збережено для {chat_id}")
    except Exception as e:
        logger.error(f"Не вдалося зберегти лог для {chat_id}: {e}")

# --- Обробники ---
async def start(update, context):
    """Надсилає персоналізоване вітальне повідомлення при команді /start."""
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    message_text = update.message.text

    reply_text = (
        f'Вітаю, {user_name}!\n\n'
        'Ласкаво просимо до сервісу TruckMaster!\n\n'
        'Наразі бот знаходиться на стадії розробки, слідкуйте за оновленнями.\n\n'
    )

    await update.message.reply_text(reply_text)

    # 2. Викликаємо логування
    await log_message(chat_id, user_name, message_text, reply_text)

async def check_order_status(update, context):
    """Обробляє текстове повідомлення та викликає синхронну функцію БД."""
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    original_text = update.message.text

    order_number = re.sub(r'\D', '', original_text)

    if not order_number:
        reply_message = f"'{original_text}' - це наразі невідома мені команда. Будь ласка, спробуйте ще раз."
        await update.message.reply_text(reply_message)
        # 3. Викликаємо логування (навіть для помилок)
        await log_message(chat_id, user_name, original_text, reply_message)
        return

    reply_message = await get_order_from_db(order_number)
    await update.message.reply_text(reply_message)

    # 4. Викликаємо логування
    await log_message(chat_id, user_name, original_text, reply_message)

@sync_to_async
def get_order_from_db(order_number):
    """
    Виконує синхронний запит до бази даних Django.
    """
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
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_order_status))

        try:
            asyncio.run(application.run_polling())
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Бот зупинено.'))