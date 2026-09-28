"""Селективне відновлення MaintenanceKitFilter/TemplateKitFilter з JSON-бекапу.

Використовується для точкового відкату після помилкового масового видалення,
не чіпаючи інші таблиці БД.

Логіка:
1) Читає JSON-бекап (формат Django dumpdata).
2) Витягує тільки записи `orders.maintenancekitfilter` і `orders.templatekitfilter`.
3) Пропускає записи, чиї FK (maintenance_kit / template / part) вже не існують
   у поточній БД (напр. кіт видалено).
4) Пропускає записи, які вже існують у БД з таким же PK.
5) Створює відсутні записи через bulk_create.

Використання:
    python manage.py restore_kit_filters_from_backup /path/to/backup.json          # dry-run
    python manage.py restore_kit_filters_from_backup /path/to/backup.json --apply  # реально
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventory.models import Product
from orders.models import (
    MaintenanceKit,
    MaintenanceKitFilter,
    MaintenanceIntervalsTemplate,
    TemplateKitFilter,
)


TARGETS = {
    'orders.maintenancekitfilter': {
        'model': MaintenanceKitFilter,
        'parent_field': 'maintenance_kit',
        'parent_model': MaintenanceKit,
    },
    'orders.templatekitfilter': {
        'model': TemplateKitFilter,
        'parent_field': 'template',
        'parent_model': MaintenanceIntervalsTemplate,
    },
}


class Command(BaseCommand):
    help = "Відновлює MaintenanceKitFilter/TemplateKitFilter з JSON-бекапу (dumpdata)."

    def add_arguments(self, parser):
        parser.add_argument('backup_path', help='Шлях до JSON-бекапу.')
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Реально створити записи (без цього — тільки показати статистику).',
        )

    def handle(self, *args, **options):
        path = Path(options['backup_path'])
        apply = options['apply']

        if not path.exists():
            raise CommandError(f'Файл не знайдено: {path}')

        self.stdout.write(f'Читаю {path} …')
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        self.stdout.write(f'  → {len(data)} записів у бекапі')

        total_created = 0
        for model_key, cfg in TARGETS.items():
            rows = [obj for obj in data if obj.get('model') == model_key]
            self.stdout.write('')
            self.stdout.write(self.style.NOTICE(f'{model_key}: у бекапі {len(rows)}'))

            model = cfg['model']
            parent_field = cfg['parent_field']
            parent_model = cfg['parent_model']

            existing_pks = set(model.objects.values_list('pk', flat=True))
            existing_parents = set(parent_model.objects.values_list('pk', flat=True))
            existing_parts = set(Product.objects.values_list('pk', flat=True))

            skipped_already_exists = 0
            skipped_missing_parent = 0
            skipped_missing_part = 0
            to_create = []

            for row in rows:
                pk = row['pk']
                fields = row['fields']
                if pk in existing_pks:
                    skipped_already_exists += 1
                    continue
                parent_id = fields.get(parent_field)
                part_id = fields.get('part')
                if parent_id not in existing_parents:
                    skipped_missing_parent += 1
                    continue
                if part_id not in existing_parts:
                    skipped_missing_part += 1
                    continue
                kwargs = {'pk': pk}
                kwargs[f'{parent_field}_id'] = parent_id
                kwargs['part_id'] = part_id
                for k, v in fields.items():
                    if k in (parent_field, 'part'):
                        continue
                    kwargs[k] = v
                to_create.append(model(**kwargs))

            self.stdout.write(f'  → до створення: {len(to_create)}')
            self.stdout.write(f'  → пропущено (вже існує): {skipped_already_exists}')
            self.stdout.write(f'  → пропущено (нема батька): {skipped_missing_parent}')
            self.stdout.write(f'  → пропущено (нема part): {skipped_missing_part}')

            if apply and to_create:
                with transaction.atomic():
                    model.objects.bulk_create(to_create, batch_size=500)
                self.stdout.write(self.style.SUCCESS(f'  → створено {len(to_create)}'))
                total_created += len(to_create)

        self.stdout.write('')
        if apply:
            self.stdout.write(self.style.SUCCESS(f'Разом створено {total_created} записів.'))
        else:
            self.stdout.write(self.style.NOTICE(
                'Це dry-run; додайте --apply для реального створення.'
            ))
