from django.apps import AppConfig


class AlprConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'alpr'
    verbose_name = 'Розпізнавання номерів'

    MODULE_INFO = {
        'name': 'alpr',
        'label': 'Розпізнавання номерів',
        'description': 'ALPR камера: розпізнавання номерних знаків, журнал заїздів.',
        'is_core': False,
        'url_prefixes': ['/api/alpr/'],
        'dependencies': ['clients'],
        'order': 9,
    }

    def ready(self):
        from core.registry import register_module
        register_module(self.MODULE_INFO)
