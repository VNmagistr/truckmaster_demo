from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'appointments'
    verbose_name = 'Записи на СТО'

    MODULE_INFO = {
        'name': 'appointments',
        'label': 'Записи на СТО',
        'description': 'Онлайн-запис клієнтів, статуси, прив\'язка до замовлень.',
        'is_core': False,
        'url_prefixes': ['/api/appointments/'],
        'dependencies': ['clients'],
        'order': 8,
    }

    def ready(self):
        from core.registry import register_module
        register_module(self.MODULE_INFO)

        import appointments.signals  # noqa
