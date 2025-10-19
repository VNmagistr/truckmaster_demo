import os
import requests
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Налаштовуємо логування, щоб бачити помилки
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Налаштування ---
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
API_SECRET_KEY = os.environ.get('BOT_API_SECRET_KEY') # Використовуємо той самий ключ, що і в settings.py
CRM_API_URL = "http://127.0.0.1/api"

# --- Обробник команди /start ---
async def start(update, context):
    """Надсилає вітальне повідомлення при команді /start."""
    await update.message.reply_text(
        'Ласкаво просимо до сервісу TruckMaster!\n\n'
        'Щоб перевірити статус вашого наряд-замовлення, просто надішліть мені його номер.'
    )

# --- Обробник текстових повідомлень (для перевірки статусу) ---
async def check_order_status(update, context):
    """Перевіряє статус замовлення за його номером."""
    order_number = update.message.text
    
    headers = {
        'X-BOT-API-SECRET': API_SECRET_KEY
    }
    
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
            await update.message.reply_text(f"Замовлення з номером {order_number} не знайдено. Будь ласка, перевірте номер.")
        
        elif e.response.status_code == 400:
            await update.message.reply_text(f"'{order_number}' - це некоректний номер. Будь ласка, надішліть лише номер замовлення (цифрами).")
            logger.error(f"Bad Request: 400. Input was: {order_number}")
        
        else: # Обробка 500 та інших помилок
            await update.message.reply_text("Виникла помилка на сервері. Ми вже працюємо над цим.")
            logger.error(f"Server error: {e.response.status_code}")
            
    except requests.exceptions.RequestException as e:
        await update.message.reply_text("Не вдалося підключитися до сервісу. Спробуйте пізніше.")
        logger.error(f"Connection error: {e}")

# --- Головна функція запуску бота (тепер НЕ асинхронна) ---
def main():
    """Запускає бота."""
    if not BOT_TOKEN or not API_SECRET_KEY:
        logger.error("ПОМИЛКА: Необхідно встановити змінні оточення TELEGRAM_BOT_TOKEN та BOT_API_SECRET_KEY")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_order_status))

    print("Бот запущений...")
    application.run_polling()

if __name__ == '__main__':
    main()