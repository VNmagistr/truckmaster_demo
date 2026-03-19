# core/management/commands/init_modules.py
# Запускати після першого `migrate`: python manage.py init_modules

from django.core.management.base import BaseCommand

from core.models import Module
from core.registry import get_registry


class Command(BaseCommand):
    help = 'Синхронізує реєстр модулів з базою даних (метадані). is_enabled не перезаписується.'

    def handle(self, *args, **options):
        registry = get_registry()

        if not registry:
            self.stdout.write(self.style.WARNING(
                'Реєстр порожній. Переконайтесь, що Django повністю завантажений.'
            ))
            return

        created_count = 0
        updated_count = 0

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

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  [+] Створено: {name}'))
            else:
                # Оновлюємо метадані, але не чіпаємо is_enabled
                module.label = info['label']
                module.description = info.get('description', '')
                module.is_core = info.get('is_core', False)
                module.url_prefixes = info.get('url_prefixes', [])
                module.dependencies = info.get('dependencies', [])
                module.order = info.get('order', 0)
                module.save()
                updated_count += 1
                self.stdout.write(f'  [~] Оновлено: {name}')

        self.stdout.write(self.style.SUCCESS(
            f'\nГотово. Створено: {created_count}, Оновлено: {updated_count}.'
        ))
