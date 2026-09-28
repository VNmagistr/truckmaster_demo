"""Видалення олив, помилково доданих у фільтри комплектів ТО.

Причина: signal `auto_save_maintenance_kit` до фіксу визначав оливу лише за
`product.subcategory.category.category_type`. Якщо у товару категорія
проставлена некоректно (наприклад, для трансмісійної оливи), він потрапляв у
`MaintenanceKitFilter` як фільтр. Цей скрипт знаходить і видаляє такі записи.

Використання:
    python manage.py cleanup_oil_in_filters            # dry-run (показує що видалить)
    python manage.py cleanup_oil_in_filters --apply    # реально видалити
"""
from django.core.management.base import BaseCommand
from django.db.models import Q

from orders.models import (
    MaintenanceKitFilter,
    BaseMaintenanceKitFilter,
    TemplateKitFilter,
)
from orders.signals import OIL_CATEGORY_TYPES, _OIL_NAME_KW


def _oil_filter_queryset(model):
    """Повертає записи, у яких part — олива (за category_type або назвою)."""
    name_q = Q()
    for kw in _OIL_NAME_KW:
        name_q |= Q(part__name__icontains=kw)
    cat_q = Q(part__subcategory__category__category_type__in=list(OIL_CATEGORY_TYPES))
    return model.objects.filter(cat_q | name_q).select_related('part')


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
            qs = _oil_filter_queryset(model)
            count = qs.count()
            total += count
            self.stdout.write(self.style.WARNING(f'{label}: знайдено {count} записів'))
            for item in qs:
                self.stdout.write(f'  #{item.pk} → [{item.part.sku_code}] {item.part.name}')
            if apply and count:
                qs.delete()
                self.stdout.write(self.style.SUCCESS(f'  → видалено {count}'))

        if not apply:
            self.stdout.write('')
            self.stdout.write(self.style.NOTICE(
                f'Разом знайдено {total} записів. Це dry-run; додайте --apply для видалення.'
            ))
        else:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'Разом видалено {total} записів.'))
