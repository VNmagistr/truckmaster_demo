from django.apps import AppConfig


class ClientsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clients'

    MODULE_INFO = {
        'name': 'clients',
        'label': 'Клієнти та автомобілі',
        'description': 'База клієнтів, вантажівок та моделей Iveco.',
        'is_core': True,
        'url_prefixes': ['/api/clients/', '/api/trucks/', '/api/base-models/'],
        'dependencies': [],
        'order': 2,
    }

    def ready(self):
        from core.registry import register_module
        register_module(self.MODULE_INFO)

        from django.db.models.signals import post_save
        from django.dispatch import receiver
        from clients.models import Client, ClientFeature

        @receiver(post_save, sender=Client)
        def auto_create_client_features(sender, instance, created, **kwargs):
            if created:
                ClientFeature.objects.get_or_create(client=instance)
