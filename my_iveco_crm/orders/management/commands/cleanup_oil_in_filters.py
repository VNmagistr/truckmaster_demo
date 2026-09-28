"""Видалення олив, помилково доданих у фільтри комплектів ТО.

Використовує `orders.signals._is_oil_product` — ту саму логіку, що і signal:
"мастило" вимагає щоб назва починалась з "Олив/Масл/Мастил/Oil" АБО щоб
category_type був у {oil, олива, масло, мастило}, І при цьому назва НЕ містила
жодного з ключових слів запчастин (фільтр/шайба/прокладка/...).

Використання:
    python manage.py cleanup_oil_in_filters            # dry-run (показує що видалить)
    python manage.py cleanup_oil_in_filters --apply    # реально видалити
"""
from django.core.management.base import BaseCommand

from orders.models import (
    MaintenanceKitFilter,
    BaseMaintenanceKitFilter,
    TemplateKitFilter,
)
from orders.signals import _is_oil_product


class Command(BaseCommand):
    help = "Видаляє MaintenanceKitFilter/BaseMaintenanceKitFilter/TemplateKitFilter, у яких part — олива."

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Реально видалити знайдені записи (без цього — тільки показати).',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        total = 0

        for model, label in [
            (MaintenanceKitFilter, 'MaintenanceKitFilter'),
            (BaseMaintenanceKitFilter, 'BaseMaintenanceKitFilter'),
            (TemplateKitFilter, 'TemplateKitFilter'),
        ]:
            qs = model.objects.select_related(
                'part__subcategory__category',
            ).all()
            victims = [row for row in qs if _is_oil_product(row.part)]
            count = len(victims)
            total += count
            self.stdout.write(self.style.WARNING(f'{label}: знайдено {count} записів'))
            for item in victims:
                self.stdout.write(f'  #{item.pk} → [{item.part.sku_code}] {item.part.name}')
            if apply and count:
                model.objects.filter(pk__in=[v.pk for v in victims]).delete()
                self.stdout.write(self.style.SUCCESS(f'  → видалено {count}'))

        if not apply:
            self.stdout.write('')
            self.stdout.write(self.style.NOTICE(
                f'Разом знайдено {total} записів. Це dry-run; додайте --apply для видалення.'
            ))
        else:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'Разом видалено {total} записів.'))
