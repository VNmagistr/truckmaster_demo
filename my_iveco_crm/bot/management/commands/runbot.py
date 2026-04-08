"""Telegram bot management command."""
import os
import logging
from django.core.management.base import BaseCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from bot.handlers import start, handle_contact, my_cars, handle_text, admin_buttons, callback_handler, handle_photo

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run Telegram bot'

    def handle(self, *args, **options):
        if not BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN не встановлений у змінних середовища")

        app = Application.builder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
        app.add_handler(MessageHandler(filters.Regex("^Мої автомобілі"), my_cars))

        admin_regex = "^(Всі автомобілі|Всі замовлення|Статистика|Знайти авто|Знайти клієнта|📷 Фото замовлення)"
        app.add_handler(MessageHandler(filters.Regex(admin_regex), admin_buttons))

        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        app.add_handler(CallbackQueryHandler(callback_handler))

        self.stdout.write("Бот працює...")
        app.run_polling()
