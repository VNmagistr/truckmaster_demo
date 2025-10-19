# bot/management/commands/runbot.py

import os
import requests
import logging
import asyncio
from django.core.management.base import BaseCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Налаштовуємо логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Налаштування ---
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
# Читаємо той самий ключ, що і в settings.py
API_SECRET_KEY = os.environ.get('BOT_API_SECRET_KEY') 
CRM_API_URL = "http://127.0.0.1/api" # Бот спілкується з Nginx

# --- Обробники ---
async def start(update, context):
    await update.message.reply_text(
        'Ласкаво просимо до сервісу TruckMaster!\n\n'
        'Щоб перевірити статус вашого наряд-замовлення, просто надішліть мені його номер.'
    )

async def check_order_status(update, context):
    order_number = update.message.text
    headers = {'X-BOT-API-SECRET': API_SECRET_KEY}
    
    try:
        response = requests.get(
            f"{CRM_API_URL}/bot/order-status/{order_number}/", 
            headers=headers
        )
        response.raise_for_status() 
        
        data = response.json()
        reply = (
            f"Замовлення №{data.get('order_number')}\n"
            f"Статус: {data.get('status')}\n"
            f"Клієнт: {data.get('client')}\n"
            f"Вантажівка: {data.get('truck')}"
        )
        await update.message.reply_text(reply)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            await update.message.reply_text(f"Замовлення з номером {order_number} не знайдено.")
        elif e.response.status_code == 400:
            await update.message.reply_text(f"Ви надіслали '{order_number}'. Будь ласка, надішліть лише номер замовлення (цифрами).")
        else:
            await update.message.reply_text("Виникла помилка на сервері.")
            logger.error(f"Server error: {e.response.status_code}")
    except requests.exceptions.RequestException as e:
        await update.message.reply_text("Не вдалося підключитися до сервісу.")
        logger.error(f"Connection error: {e}")

# --- Клас команди Django ---
class Command(BaseCommand):
    help = 'Запускає Telegram бота'

    def handle(self, *args, **options):
        if not BOT_TOKEN or not API_SECRET_KEY:
            logger.error("ПОМИЛКА: Змінні оточення TELEGRAM_BOT_TOKEN та BOT_API_SECRET_KEY не встановлені!")
            return

        self.stdout.write(self.style.SUCCESS('Бот запускається...'))

        application = Application.builder().token(BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_order_status))

        # Використовуємо asyncio.run для запуску асинхронної функції
        try:
            asyncio.run(application.run_polling())
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Бот зупинено.'))