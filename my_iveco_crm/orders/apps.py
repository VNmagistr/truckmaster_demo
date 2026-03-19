from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'

    MODULE_INFO = {
        'name': 'orders',
        'label': 'Замовлення',
        'description': 'Сервісні замовлення, роботи, фото ремонту, набори ТО.',
        'is_core': True,
        'url_prefixes': [
            '/api/orders/', '/api/service-orders/', '/api/service-works/',
            '/api/work-groups/', '/api/work-prices/', '/api/repair-photos/',
            '/api/maintenance-rules/', '/api/maintenance-logs/',
            '/api/maintenance-kits/', '/api/maintenance-kit-filters/',
            '/api/maintenance-intervals/', '/api/base-maintenance-kits/',
        ],
        'dependencies': ['clients'],
        'order': 3,
    }

    def ready(self):
        from core.registry import register_module
        register_module(self.MODULE_INFO)

        import orders.signals  # Реєструємо сигнали

        # Підключаємо сигнал авто-збереження набору ТО до UsedPart
        # (робиться тут, а не через @receiver, щоб уникнути circular import)
        from django.db.models.signals import post_save
        from inventory.models import UsedPart
        post_save.connect(orders.signals.auto_save_maintenance_kit, sender=UsedPart)
