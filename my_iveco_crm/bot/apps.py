from django.apps import AppConfig


class BotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot'
    verbose_name = 'Telegram бот'

    MODULE_INFO = {
        'name': 'bot',
        'label': 'Telegram бот',
        'description': 'Telegram бот для сповіщень клієнтів та персоналу.',
        'is_core': False,
        'url_prefixes': ['/api/bot/'],
        'dependencies': [],
        'order': 7,
    }

    def ready(self):
        from core.registry import register_module
        register_module(self.MODULE_INFO)
