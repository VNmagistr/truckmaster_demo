# core/apps.py

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Система модулів'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(_sync_modules_after_migrate, sender=self)


def _sync_modules_after_migrate(sender, **kwargs):
    """Автоматично синхронізує реєстр модулів з БД після кожного migrate."""
    from core.models import Module
    from core.registry import get_registry

    registry = get_registry()
    if not registry:
        return

    for name, info in registry.items():
        module, created = Module.objects.get_or_create(
            name=name,
            defaults={
                'label': info['label'],
                'description': info.get('description', ''),
                'is_enabled': True,
                'is_core': info.get('is_core', False),
                'url_prefixes': info.get('url_prefixes', []),
                'dependencies': info.get('dependencies', []),
                'order': info.get('order', 0),
            },
        )
        if not created:
            # Оновлюємо метадані, але не чіпаємо is_enabled
            module.label = info['label']
            module.description = info.get('description', '')
            module.is_core = info.get('is_core', False)
            module.url_prefixes = info.get('url_prefixes', [])
            module.dependencies = info.get('dependencies', [])
            module.order = info.get('order', 0)
            module.save()
