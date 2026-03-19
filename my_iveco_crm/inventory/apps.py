from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'
    verbose_name = 'Склад'

    MODULE_INFO = {
        'name': 'inventory',
        'label': 'Склад',
        'description': 'Склад запчастин, рух товарів, залишки на складах.',
        'is_core': False,
        'url_prefixes': ['/api/inventory/'],
        'dependencies': [],
        'order': 4,
    }

    def ready(self):
        from core.registry import register_module
        register_module(self.MODULE_INFO)

        import inventory.signals
