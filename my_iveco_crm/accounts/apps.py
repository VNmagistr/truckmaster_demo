from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    MODULE_INFO = {
        'name': 'accounts',
        'label': 'Аутентифікація',
        'description': 'Вхід персоналу, реєстрація, відгуки Google, QR-коди.',
        'is_core': True,
        'url_prefixes': ['/api/token/', '/api/register/', '/api/contact/', '/api/places-reviews/', '/api/qr/'],
        'dependencies': [],
        'order': 0,
    }

    def ready(self):
        from core.registry import register_module
        register_module(self.MODULE_INFO)
