from django.apps import AppConfig


class ShortlinksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shortlinks'

    MODULE_INFO = {
        'name': 'shortlinks',
        'label': 'Короткі посилання (QR)',
        'description': (
            'Редіректи виду /go/<slug> для друку QR на поліграфії — '
            'посилання можна змінювати без передруку.'
        ),
        'is_core': True,
        'url_prefixes': ['/go/'],
        'dependencies': [],
        'order': 1,
    }

    def ready(self):
        from core.registry import register_module
        register_module(self.MODULE_INFO)
