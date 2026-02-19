# bot/utils.py

"""
Допоміжні функції для Telegram бота
"""

import logging
import time
from functools import wraps
from typing import Optional
from asgiref.sync import sync_to_async

from telegram import Update
from telegram.ext import ContextTypes

from .models import BotUser, BotMessageLog

logger = logging.getLogger(__name__)


# ========== ДЕКОРАТОРИ ==========

def require_role(*allowed_roles):
    """
    Декоратор для перевірки ролі користувача

    Використання:
        @require_role('owner', 'admin')
        async def my_handler(update, context):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user

            try:
                bot_user = await sync_to_async(BotUser.objects.get)(telegram_id=user.id)

                if bot_user.role in allowed_roles or bot_user.role == 'admin':
                    return await func(update, context, *args, **kwargs)
                else:
                    await update.message.reply_text(
                        "⛔ У вас немає доступу до цієї команди."
                    )
                    return None

            except BotUser.DoesNotExist:
                await update.message.reply_text(
                    "❌ Користувача не знайдено. Використайте /start для реєстрації."
                )
                return None

        return wrapper
    return decorator


def log_message(func):
    """
    Декоратор для логування повідомлень
    Автоматично зберігає повідомлення в БД
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        start_time = time.time()
        user = update.effective_user
        message = update.message or update.callback_query.message

        # Визначаємо тип повідомлення
        message_type = 'text'
        message_text = ''

        if update.message:
            if update.message.text:
                message_type = 'command' if update.message.text.startswith('/') else 'text'
                message_text = update.message.text
            elif update.message.contact:
                message_type = 'contact'
                message_text = f"Contact: {update.message.contact.phone_number}"
            elif update.message.photo:
                message_type = 'photo'
                message_text = "Photo"
            elif update.message.document:
                message_type = 'document'
                message_text = f"Document: {update.message.document.file_name}"
            elif update.message.location:
                message_type = 'location'
                message_text = "Location"
        elif update.callback_query:
            message_type = 'callback'
            message_text = update.callback_query.data

        try:
            # Викликаємо оригінальну функцію
            result = await func(update, context, *args, **kwargs)

            # Зберігаємо в БД
            try:
                bot_user = await sync_to_async(BotUser.objects.get)(telegram_id=user.id)

                await sync_to_async(BotMessageLog.objects.create)(
                    bot_user=bot_user,
                    message_type=message_type,
                    is_incoming=True,
                    message_text=message_text,
                    is_processed=True,
                )

            except Exception as e:
                logger.error(f"Error logging message: {e}")

            return result

        except Exception as e:
            # Логуємо помилку
            try:
                bot_user = await sync_to_async(BotUser.objects.get)(telegram_id=user.id)
                await sync_to_async(BotMessageLog.objects.create)(
                    bot_user=bot_user,
                    message_type=message_type,
                    is_incoming=True,
                    message_text=message_text,
                    is_processed=False,
                )
            except Exception as log_error:
                logger.error(f"Error logging error message: {log_error}")

            # Перекидаємо помилку далі
            raise

    return wrapper


# ========== ФУНКЦІЇ ДЛЯ РОБОТИ З БД ==========

@sync_to_async
def get_or_create_bot_user(telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> BotUser:
    """Отримує або створює користувача бота"""
    bot_user, created = BotUser.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={
            'username': username,
            'first_name': first_name or '',
            'last_name': last_name or '',
        }
    )

    # Оновлюємо дані якщо вони змінились
    if not created:
        updated = False
        if username and bot_user.username != username:
            bot_user.username = username
            updated = True
        if first_name and bot_user.first_name != first_name:
            bot_user.first_name = first_name
            updated = True
        if last_name and bot_user.last_name != last_name:
            bot_user.last_name = last_name
            updated = True

        if updated:
            bot_user.save()

    return bot_user


@sync_to_async
def get_bot_user(telegram_id: int) -> Optional[BotUser]:
    """Отримує користувача бота"""
    try:
        return BotUser.objects.get(telegram_id=telegram_id)
    except BotUser.DoesNotExist:
        return None


@sync_to_async
def get_user_trucks(bot_user: BotUser):
    """Отримує список автомобілів користувача"""
    if bot_user.role == 'owner' and bot_user.client:
        from clients.models import Truck
        return list(Truck.objects.filter(client=bot_user.client))
    return []


# ========== ФОРМАТУВАННЯ ==========

def format_phone_number(phone: str) -> str:
    """
    Форматує номер телефону
    +380501234567 -> +38 (050) 123-45-67
    """
    if not phone:
        return ""

    # Видаляємо всі символи крім цифр і +
    clean = ''.join(c for c in phone if c.isdigit() or c == '+')

    # Якщо починається з 380
    if clean.startswith('+380') and len(clean) == 13:
        return f"+38 ({clean[3:6]}) {clean[6:9]}-{clean[9:11]}-{clean[11:]}"

    return phone


def format_truck_info(truck) -> str:
    """Форматує інформацію про автомобіль"""
    info = f"🚚 {truck.specific_model_name}\n"
    info += f"📋 Номер: {truck.license_plate}\n"
    info += f"🔢 VIN: ...{truck.last_seven_vin}\n"

    if truck.euro_standard:
        info += f"♻️ Євростандарт: {truck.get_euro_standard_display()}\n"

    return info


def format_order_info(order) -> str:
    """Форматує інформацію про замовлення"""
    info = f"📝 Замовлення #{order.order_number}\n"
    info += f"📅 Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    info += f"📊 Статус: {order.get_status_display()}\n"

    if order.truck:
        info += f"🚚 Автомобіль: {order.truck.license_plate}\n"

    if order.problem_description:
        info += f"📝 Опис: {order.problem_description[:100]}\n"

    if order.total_cost:
        info += f"💰 Вартість: {order.total_cost} грн\n"

    return info


def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрізає текст до вказаної довжини"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


# ========== ВАЛІДАЦІЯ ==========

def is_valid_license_plate(plate: str) -> bool:
    """Перевіряє чи коректний номер автомобіля"""
    import re
    # Українські номери: AA1234BB або AA1234AA
    pattern = r'^[АВЕКМНОРСТУХ]{2}\d{4}[АВЕКМНОРСТУХ]{2}$'
    return bool(re.match(pattern, plate.upper()))


def extract_order_number(text: str) -> Optional[str]:
    """Витягує номер замовлення з тексту"""
    import re
    # Шукаємо цифри
    digits = re.findall(r'\d+', text)
    return digits[0] if digits else None


# ========== ПОМІЧНИКИ ==========

async def send_long_message(update: Update, text: str, max_length: int = 4096):
    """
    Відправляє довге повідомлення, розбиваючи його на частини якщо потрібно
    Telegram має ліміт 4096 символів на повідомлення
    """
    if len(text) <= max_length:
        await update.message.reply_text(text)
        return

    # Розбиваємо на частини
    parts = []
    current_part = ""

    for line in text.split('\n'):
        if len(current_part) + len(line) + 1 <= max_length:
            current_part += line + '\n'
        else:
            if current_part:
                parts.append(current_part)
            current_part = line + '\n'

    if current_part:
        parts.append(current_part)

    # Відправляємо частинами
    for i, part in enumerate(parts, 1):
        header = f"📄 Частина {i}/{len(parts)}\n\n" if len(parts) > 1 else ""
        await update.message.reply_text(header + part)


def escape_markdown(text: str) -> str:
    """Екранує спеціальні символи для Markdown"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text
