# bot/handlers/common.py

"""
Загальні обробники команд для всіх користувачів
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from ..models import BotUser
from ..keyboards import get_main_keyboard_for_role, get_guest_keyboard
from ..utils import get_or_create_bot_user, log_message
from ..services import UserService, CommandService

logger = logging.getLogger(__name__)


@log_message
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /start - вітання та реєстрація користувача
    """
    user = update.effective_user
    
    # Реєструємо використання команди
    await CommandService.register_command_usage('/start')
    
    # Отримуємо або створюємо користувача
    bot_user, created = await UserService.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name or '',
        last_name=user.last_name or ''
    )
    
    # Формуємо привітання
    greeting = f"👋 Вітаю, {user.first_name}!\n\n"
    
    if created:
        greeting += (
            "Це бот сервісного центру Iveco.\n\n"
            "Для повноцінної роботи мені потрібен ваш номер телефону, "
            "щоб знайти вас у нашій базі клієнтів.\n\n"
            "Будь ласка, натисніть кнопку нижче, щоб надати контакт."
        )
        keyboard = get_guest_keyboard()
    else:
        if bot_user.client:
            greeting += f"Рада бачити вас знову!\n"
            greeting += f"Ваш статус: {bot_user.get_role_display()}\n\n"
            greeting += "Оберіть опцію з меню нижче:"
            keyboard = get_main_keyboard_for_role(bot_user.role)
        else:
            greeting += (
                "Ви вже зареєстровані, але ще не прив'язані до клієнта.\n"
                "Будь ласка, надайте ваш номер телефону."
            )
            keyboard = get_guest_keyboard()
    
    await update.message.reply_text(greeting, reply_markup=keyboard)


@log_message
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /help - допомога
    """
    user = update.effective_user
    
    await CommandService.register_command_usage('/help')
    
    bot_user = await UserService.get_user_by_telegram_id(user.id)
    
    help_text = "📚 *Довідка по боту*\n\n"
    
    if not bot_user or bot_user.role == 'guest':
        help_text += (
            "*Загальні команди:*\n"
            "/start - Почати роботу з ботом\n"
            "/help - Показати цю довідку\n\n"
            "Для повноцінної роботи надайте свій номер телефону, "
            "натиснувши відповідну кнопку."
        )
    else:
        help_text += "*Доступні команди:*\n\n"
        
        if bot_user.role in ['driver', 'owner', 'manager', 'admin']:
            help_text += (
                "🚚 *Автомобілі:*\n"
                "/mycars - Мої автомобілі\n"
                "/truck - Інформація про автомобіль\n\n"
                
                "📝 *Замовлення:*\n"
                "/order - Перевірити замовлення\n"
                "/history - Історія ремонтів\n\n"
            )
        
        if bot_user.role in ['owner', 'driver']:
            help_text += (
                "🔔 *Нагадування:*\n"
                "/reminders - Налаштування нагадувань\n\n"
            )
        
        if bot_user.role in ['manager', 'admin']:
            help_text += (
                "🔍 *Пошук:*\n"
                "/search - Знайти автомобіль\n\n"
            )
        
        if bot_user.role == 'admin':
            help_text += (
                "⚙️ *Адміністрування:*\n"
                "/logs - Переглянути логи\n"
                "/stats - Статистика бота\n\n"
            )
        
        help_text += (
            "*Загальні:*\n"
            "/settings - Налаштування\n"
            "/help - Ця довідка\n"
            "/cancel - Скасувати поточну дію"
        )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


@log_message
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /cancel - скасування поточної операції
    """
    user = update.effective_user
    
    bot_user = await UserService.get_user_by_telegram_id(user.id)
    
    if bot_user:
        from ..utils import reset_conversation_state
        await reset_conversation_state(bot_user)
        
        keyboard = get_main_keyboard_for_role(bot_user.role)
        await update.message.reply_text(
            "✅ Операцію скасовано. Повертаємось до головного меню.",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            "✅ Операцію скасовано.",
            reply_markup=get_guest_keyboard()
        )


@log_message
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /settings - налаштування
    """
    user = update.effective_user
    
    bot_user = await UserService.get_user_by_telegram_id(user.id)
    
    if not bot_user:
        await update.message.reply_text(
            "❌ Спочатку зареєструйтесь за допомогою /start"
        )
        return
    
    settings_text = "⚙️ *Ваші налаштування:*\n\n"
    settings_text += f"👤 Ім'я: {bot_user.get_full_name()}\n"
    settings_text += f"📱 Telegram: @{bot_user.username or 'не вказано'}\n"
    settings_text += f"📞 Телефон: {bot_user.phone_number or 'не вказано'}\n"
    settings_text += f"👔 Роль: {bot_user.get_role_display()}\n"
    settings_text += f"🌐 Мова: {bot_user.language_code}\n"
    settings_text += f"🔔 Сповіщення: {'увімкнені' if bot_user.notifications_enabled else 'вимкнені'}\n\n"
    
    if bot_user.client:
        settings_text += f"🏢 Клієнт: {bot_user.client.name}\n"
    
    settings_text += "\nДля зміни налаштувань зверніться до адміністратора."
    
    await update.message.reply_text(settings_text, parse_mode='Markdown')


@log_message
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробник отримання контакту користувача
    """
    user = update.effective_user
    contact = update.message.contact
    
    # Перевіряємо, що це контакт самого користувача
    if contact.user_id != user.id:
        await update.message.reply_text(
            "⚠️ Будь ласка, надішліть свій власний контакт, а не чужий."
        )
        return
    
    phone_number = contact.phone_number
    
    # Отримуємо користувача
    bot_user = await UserService.get_user_by_telegram_id(user.id)
    
    if not bot_user:
        # Створюємо нового користувача
        bot_user, created = await UserService.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name or '',
            last_name=user.last_name or '',
            phone_number=phone_number
        )
    
    # Прив'язуємо до клієнта
    success, message = await UserService.link_user_with_client(bot_user, phone_number)
    
    # Оновлюємо користувача після прив'язки
    bot_user = await UserService.get_user_by_telegram_id(user.id)
    
    keyboard = get_main_keyboard_for_role(bot_user.role)
    await update.message.reply_text(message, reply_markup=keyboard)


@log_message
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробник невідомих команд
    """
    await update.message.reply_text(
        "❓ Вибачте, я не розумію цю команду.\n"
        "Використайте /help щоб побачити список доступних команд."
    )


@log_message
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробник текстових повідомлень (кнопки меню)
    """
    text = update.message.text
    user = update.effective_user
    
    bot_user = await UserService.get_user_by_telegram_id(user.id)
    
    if not bot_user:
        await update.message.reply_text(
            "Будь ласка, спочатку зареєструйтесь за допомогою /start"
        )
        return
    
    # Обробка загальних кнопок
    if text == "ℹ️ Інформація":
        info_text = (
            "ℹ️ *Про сервісний центр*\n\n"
            "Ми спеціалізуємось на обслуговуванні та ремонті вантажівок Iveco.\n\n"
            "📍 Адреса: [вказати адресу]\n"
            "📞 Телефон: [вказати телефон]\n"
            "🕐 Графік роботи: Пн-Пт 9:00-18:00\n\n"
            "Використайте /help для перегляду команд."
        )
        await update.message.reply_text(info_text, parse_mode='Markdown')
        
    elif text == "❓ Допомога":
        await help_command(update, context)
        
    elif text == "⚙️ Налаштування":
        await settings_command(update, context)
        
    else:
        # Якщо це просто текст - можливо номер замовлення
        await update.message.reply_text(
            "Якщо ви хочете перевірити замовлення, використайте команду /order\n"
            "Або оберіть опцію з меню."
        )


# ========== ЕКСПОРТ ОБРОБНИКІВ ==========

# Загальні обробники (для всіх користувачів)
start_handler = CommandHandler('start', start_command)
help_handler = CommandHandler('help', help_command)
cancel_handler = CommandHandler('cancel', cancel_command)
settings_handler = CommandHandler('settings', settings_command)

# Обробник контактів
contact_message_handler = MessageHandler(filters.CONTACT, contact_handler)

# Обробник текстових повідомлень
text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler)

# Обробник невідомих команд
unknown_command_handler = MessageHandler(filters.COMMAND, unknown_command)