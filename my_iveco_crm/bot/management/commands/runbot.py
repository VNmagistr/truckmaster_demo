# bot/management/commands/runbot.py

"""
Django management команда для запуску Telegram бота
Використання: python manage.py runbot
"""

import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings

from telegram.ext import Application

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Запускає Telegram бота'

    def handle(self, *args, **options):
        """Основний метод запуску бота"""
        
        # Отримуємо токен з оточення
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        
        if not bot_token:
            self.stdout.write(
                self.style.ERROR('❌ TELEGRAM_BOT_TOKEN не встановлено!')
            )
            self.stdout.write(
                self.style.WARNING('Встановіть змінну оточення TELEGRAM_BOT_TOKEN')
            )
            return
        
        self.stdout.write(self.style.SUCCESS('🤖 Запуск Telegram бота...'))
        
        try:
            # Створюємо application
            application = Application.builder().token(bot_token).build()
            
            # Реєструємо всі обробники
            self.register_handlers(application)
            
            self.stdout.write(self.style.SUCCESS('✅ Бот успішно запущено!'))
            self.stdout.write(self.style.SUCCESS('Бот очікує повідомлень...'))
            
            # Запускаємо бота
            application.run_polling(
                allowed_updates=['message', 'callback_query', 'inline_query']
            )
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n⚠️ Отримано сигнал зупинки'))
            self.stdout.write(self.style.SUCCESS('👋 Бот зупинено'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Критична помилка: {e}'))
            logger.exception("Критична помилка при запуску бота")
            raise
    
    def register_handlers(self, application):
        """
        Реєструє всі обробники команд та повідомлень
        Порядок важливий! Більш специфічні обробники мають бути першими
        """
        from bot.handlers.common import (
            start_handler, help_handler, cancel_handler, settings_handler,
            contact_message_handler, text_handler, unknown_command_handler
        )
        from bot.handlers.driver import driver_handlers
        from bot.handlers.owner import owner_handlers
        from bot.handlers.manager import manager_handlers
        from bot.handlers.admin import admin_handlers
        
        self.stdout.write(self.style.SUCCESS('📝 Реєстрація обробників...'))
        
        # 1. ЗАГАЛЬНІ КОМАНДИ (для всіх)
        application.add_handler(start_handler)
        application.add_handler(help_handler)
        application.add_handler(cancel_handler)
        application.add_handler(settings_handler)
        
        # 2. АДМІН КОМАНДИ (найвищий пріоритет)
        for handler in admin_handlers:
            application.add_handler(handler)
        self.stdout.write('  ✓ Адмін обробники')
        
        # 3. МЕНЕДЖЕР КОМАНДИ
        for handler in manager_handlers:
            application.add_handler(handler)
        self.stdout.write('  ✓ Менеджер обробники')
        
        # 4. ВЛАСНИК КОМАНДИ
        for handler in owner_handlers:
            application.add_handler(handler)
        self.stdout.write('  ✓ Власник обробники')
        
        # 5. ВОДІЙ КОМАНДИ
        for handler in driver_handlers:
            application.add_handler(handler)
        self.stdout.write('  ✓ Водій обробники')
        
        # 6. ОБРОБНИК КОНТАКТІВ (високий пріоритет)
        application.add_handler(contact_message_handler)
        self.stdout.write('  ✓ Обробник контактів')
        
        # 7. ОБРОБНИК ТЕКСТОВИХ ПОВІДОМЛЕНЬ (низький пріоритет)
        application.add_handler(text_handler)
        self.stdout.write('  ✓ Обробник текстових повідомлень')
        
        # 8. ОБРОБНИК НЕВІДОМИХ КОМАНД (найнижчий пріоритет)
        application.add_handler(unknown_command_handler)
        self.stdout.write('  ✓ Обробник невідомих команд')
        
        self.stdout.write(self.style.SUCCESS('✅ Всі обробники зареєстровані'))
        
        # Виводимо список доступних команд
        self.stdout.write('\n📋 Доступні команди:')
        self.stdout.write('  Загальні: /start, /help, /cancel, /settings')
        self.stdout.write('  Водій/Власник: /mycars, /reminders, /order, /history, /active, /contacts')
        self.stdout.write('  Менеджер: /search, /clients, /notify')
        self.stdout.write('  Адмін: /find, /logs, /stats, /users, /broadcast')
        self.stdout.write('')