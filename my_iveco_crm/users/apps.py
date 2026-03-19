from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    MODULE_INFO = {
        'name': 'users',
        'label': 'Користувачі',
        'description': 'Управління персоналом та правами доступу.',
        'is_core': True,
        'url_prefixes': ['/api/users/'],
        'dependencies': [],
        'order': 1,
    }

    def ready(self):
        from core.registry import register_module
        register_module(self.MODULE_INFO)
