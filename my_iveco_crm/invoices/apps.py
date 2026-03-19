from django.apps import AppConfig


class InvoicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'invoices'
    verbose_name = 'Рахунки на запчастини'

    MODULE_INFO = {
        'name': 'invoices',
        'label': 'Рахунки на запчастини',
        'description': 'Рахунки для продажу запчастин поза сервісом.',
        'is_core': False,
        'url_prefixes': ['/api/invoices/', '/api/invoice-items/'],
        'dependencies': ['inventory'],
        'order': 10,
    }

    def ready(self):
        from core.registry import register_module
        register_module(self.MODULE_INFO)
