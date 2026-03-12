from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'appointments'
    verbose_name = 'Записи на СТО'

    def ready(self):
        import appointments.signals  # noqa
