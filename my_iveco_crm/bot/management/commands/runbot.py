import os
import logging
import asyncio
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from orders.models import ServiceOrder
from asgiref.sync import sync_to_async

# Налаштовуємо логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Налаштування ---
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# --- Обробники ---
async def start(update, context):
    """Надсилає персоналізоване вітальне повідомлення при команді /start."""
    
    # Отримуємо ім'я користувача з об'єкта update
    user_name = update.message.from_user.first_name
    
    # Створюємо персоналізоване повідомлення
    welcome_message = (
        f'Вітаю, {user_name}!\n\n'
        'Ласкаво просимо до сервісу TruckMaster!\n\n'
    )
    
    await update.message.reply_text(welcome_message)

async def check_order_status(update, context):
    """Обробляє текстове повідомлення та викликає синхронну функцію БД."""
    original_text = update.message.text
    order_number = re.sub(r'\D', '', original_text)
    
    if not order_number:
        await update.message.reply_text(f"'{original_text}' - це некоректний номер. Будь ласка, надішліть лише номер замовлення (цифрами).")
        return

    reply_message = await get_order_from_db(order_number)
    await update.message.reply_text(reply_message)

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