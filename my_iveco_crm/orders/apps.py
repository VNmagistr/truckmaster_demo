from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "orders"

    def ready(self):
        import orders.signals  # Реєструємо наші сигнали

        # Підключаємо сигнал авто-збереження набору ТО до UsedPart
        # (робиться тут, а не через @receiver, щоб уникнути circular import)
        from django.db.models.signals import post_save
        from inventory.models import UsedPart
        post_save.connect(orders.signals.auto_save_maintenance_kit, sender=UsedPart)