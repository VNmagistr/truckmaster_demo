import os
import logging
import asyncio
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from orders.models import ServiceOrder
from clients.models import Client # <-- Імпортуємо Client
from bot.models import BotMessageLog
from asgiref.sync import sync_to_async

# ... (код логування та BOT_TOKEN) ...
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
logger = logging.getLogger(__name__)

# --- Функції роботи з БД ---

@sync_to_async
def check_if_user_is_linked(chat_id):
    """
    Перевіряє, чи цей chat_id вже прив'язаний до якогось клієнта.
    """
    return Client.objects.filter(telegram_chat_id=chat_id).exists()

@sync_to_async
def link_client_by_phone(chat_id, user_name, phone_number):
    """
    Знаходить клієнта за номером телефону та прив'язує до нього chat_id.
    """
    try:
        # Очищуємо номер телефону (прибираємо +)
        clean_phone = phone_number.replace('+', '')

        # Шукаємо клієнта, який містить цей номер
        client = Client.objects.get(phone__contains=clean_phone)

        # Знайшли! Прив'язуємо chat_id
        client.telegram_chat_id = chat_id
        # Можемо також оновити ім'я клієнта, якщо воно не заповнене
        if not client.name:
            client.name = user_name
        client.save()

        return (
            f"Дякую, {user_name}! Я знайшов вас у базі.\n"
            f"Ваш профіль клієнта '{client.name}' успішно прив'язано до цього чату."
        )
    except Client.DoesNotExist:
        return (
            f"Дякую, {user_name}! На жаль, я не знайшов клієнта з номером {phone_number} у нашій базі. "
            "Зверніться до менеджера для реєстрації."
        )
    except Client.MultipleObjectsReturned:
        return (
            f"Виникла помилка: з номером {phone_number} знайдено декілька клієнтів. "
            "Будь ласка, зверніться до менеджера для вирішення."
        )
    except Exception as e:
        logger.error(f"Помилка прив'язки клієнта: {e}")
        return "Виникла невідома помилка. Будь ласка, спробуйте пізніше."

@sync_to_async
def log_message(chat_id, user_name, message_text, bot_response, phone_number=None):
    """
    Асинхронно зберігає повідомлення та відповідь бота у базу даних.
    """
    try:
        if not phone_number:
            client = Client.objects.filter(telegram_chat_id=chat_id).first()
            if client and client.phone:
                phone_number = client.phone

        BotMessageLog.objects.create(
            chat_id=chat_id,
            user_name=user_name,
            phone_number=phone_number,
            message_text=message_text,
            bot_response=bot_response
        )
        logger.info(f"Лог збережено для {chat_id}")
    except Exception as e:
        logger.error(f"Не вдалося зберегти лог для {chat_id}: {e}")

# --- Обробники ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Вітає користувача. Перевіряє, чи він вже прив'язаний до CRM.
    """
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    message_text = update.message.text

    # 1. Перевіряємо, чи користувач вже прив'язаний
    is_linked = await check_if_user_is_linked(chat_id)

    if is_linked:
        # 2. Якщо так, просто вітаємось
        reply_text = (
            f'Вітаю знову, {user_name}!\n\n'
            'Як Ваші справи?'
        )
        await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())

    else:
        # 3. Якщо ні, просимо номер
        contact_keyboard = KeyboardButton(text="Надати номер телефону", request_contact=True)
        custom_keyboard = [[contact_keyboard]]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True, one_time_keyboard=True)

        reply_text = (
            f'Вітаю, {user_name}!\n\n'
            'Я не впізнав вас. Для прив\'язки до вашої картки клієнта, будь ласка, поділіться номером телефону, натиснувши кнопку нижче.\n\n'
            
        )
        await update.message.reply_text(reply_text, reply_markup=reply_markup)

    await log_message(chat_id, user_name, message_text, reply_text)

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє отриманий контакт (номер телефону) і прив'язує клієнта."""
    user = update.message.from_user
    chat_id = user.id
    user_name = user.first_name
    phone_number = update.message.contact.phone_number

    # Викликаємо нову функцію прив'язки
    reply_text = await link_client_by_phone(chat_id, user_name, phone_number)

    # Відправляємо відповідь і прибираємо клавіатуру
    await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove()) 

    await log_message(chat_id, user_name, f"[Надано контакт: {phone_number}]", reply_text, phone_number=phone_number)

async def check_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє текстове повідомлення та викликає синхронну функцію БД."""
    
    user = update.message.from_user
    user_name = user.first_name
    chat_id = user.id
    original_text = update.message.text

    order_number = re.sub(r'\D', '', original_text)

    if not order_number:
        reply_message = f"'{original_text}' - це некоректний номер."
        await update.message.reply_text(reply_message)
        await log_message(chat_id, user_name, original_text, reply_message)
        return

    reply_message = await get_order_from_db(order_number)
    await update.message.reply_text(reply_message)

    await log_message(chat_id, user_name, original_text, reply_message)

@sync_to_async
def get_order_from_db(order_number):
    # ... (ця функція залишається БЕЗ ЗМІН) ...
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
    # ... (ця функція залишається БЕЗ ЗМІН) ...
    help = 'Запускає Telegram бота'

    def handle(self, *args, **options):
        if not BOT_TOKEN:
            logger.error("ПОМИЛКА: Змінна оточення TELEGRAM_BOT_TOKEN не встановлена!")
            return

        self.stdout.write(self.style.SUCCESS('Бот запускається...'))

        application = Application.builder().token(BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_order_status))

        try:
            asyncio.run(application.run_polling())
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Бот зупинено.'))