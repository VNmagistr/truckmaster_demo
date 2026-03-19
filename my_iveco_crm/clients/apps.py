from django.apps import AppConfig


class ClientsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clients'

    MODULE_INFO = {
        'name': 'clients',
        'label': 'Клієнти та автомобілі',
        'description': 'База клієнтів, вантажівок та моделей Iveco.',
        'is_core': True,
        'url_prefixes': ['/api/clients/', '/api/trucks/', '/api/base-models/'],
        'dependencies': [],
        'order': 2,
    }

    def ready(self):
        from core.registry import register_module
        register_module(self.MODULE_INFO)
