from django.apps import AppConfig


class CabinetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cabinet'
    verbose_name = 'Особистий кабінет клієнта'

    MODULE_INFO = {
        'name': 'cabinet',
        'label': 'Кабінет клієнта',
        'description': 'Особистий кабінет клієнта: замовлення, авто, профіль, окремий JWT.',
        'is_core': False,
        'url_prefixes': ['/api/cabinet/'],
        'dependencies': ['clients', 'orders'],
        'order': 6,
    }

    def ready(self):
        from core.registry import register_module
        register_module(self.MODULE_INFO)
