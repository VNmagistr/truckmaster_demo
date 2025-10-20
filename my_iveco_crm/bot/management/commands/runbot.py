import os
import logging
import asyncio
from django.core.management.base import BaseCommand
from telegram.ext import Application, CommandHandler

# Налаштовуємо логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Налаштування ---
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# --- ОБРОБНИК-ПРИВІТАННЯ ---
async def start(update, context):
    """Надсилає вітальне повідомлення при команді /start."""
    await update.message.reply_text(
        'Ласкаво просимо до сервісу TruckMaster!\n\n'
        'Наразі бот знаходиться в розробці. Слідкуйте за оновленнями.'
    )

# --- Клас команди Django ---
class Command(BaseCommand):
    help = 'Запускає Telegram бота'

    def handle(self, *args, **options):
        if not BOT_TOKEN:
            logger.error("ПОМИЛКА: Змінна оточення TELEGRAM_BOT_TOKEN не встановлена!")
            return

        self.stdout.write(self.style.SUCCESS('Бот запускається (тільки привітання)...'))

        application = Application.builder().token(BOT_TOKEN).build()

        # Додаємо лише обробник команди /start
        application.add_handler(CommandHandler("start", start))

        try:
            asyncio.run(application.run_polling())
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Бот зупинено.'))