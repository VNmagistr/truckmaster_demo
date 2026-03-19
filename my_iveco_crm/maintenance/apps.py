from django.apps import AppConfig


class MaintenanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'maintenance'

    MODULE_INFO = {
        'name': 'maintenance',
        'label': 'Технічне обслуговування',
        'description': 'Розклади ТО, нагадування клієнтам, норми регламенту.',
        'is_core': False,
        'url_prefixes': ['/api/maintenance/'],
        'dependencies': ['clients', 'orders'],
        'order': 5,
    }

    def ready(self):
        from core.registry import register_module
        register_module(self.MODULE_INFO)

        import maintenance.signals  # noqa: F401
