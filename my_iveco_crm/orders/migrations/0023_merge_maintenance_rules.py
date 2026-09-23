"""Merge E5/E6 maintenance rules into unified per-family rules.

- "Заміна оливи в двигуні STRALIS E5 (LD7)" → "Заміна оливи в двигуні STRALIS"
- "Заміна оливи в двигуні STRALIS E6" → logs reassigned to merged rule, renamed to [DEPRECATED]
- "Заміна ремнів, роликів Stralis E6" → "Заміна ремнів, роликів Stralis"
- WorkPrice "Заміна оливи в двигуні STRALIS E6" → service works reassigned, renamed to [DEPRECATED]

After migration, manually remove [DEPRECATED] entries from admin.
"""
from django.db import migrations


def merge_rules(apps, schema_editor):
    MaintenanceRule = apps.get_model('orders', 'MaintenanceRule')
    MaintenanceLog = apps.get_model('orders', 'MaintenanceLog')
    WorkPrice = apps.get_model('orders', 'WorkPrice')
    ServiceWork = apps.get_model('orders', 'ServiceWork')

    # --- 1. Merge Stralis oil rules ---
    e5_rule = MaintenanceRule.objects.filter(name__icontains='STRALIS E5').first()
    e6_rule = MaintenanceRule.objects.filter(
        name__icontains='STRALIS E6',
    ).filter(
        name__icontains='оливи',
    ).first()

    if e5_rule:
        e5_rule.name = 'Заміна оливи в двигуні STRALIS'
        e5_rule.save(update_fields=['name'])

        if e6_rule and e6_rule.pk != e5_rule.pk:
            for model in e6_rule.applicable_models.all():
                e5_rule.applicable_models.add(model)

            MaintenanceLog.objects.filter(rule=e6_rule).update(rule=e5_rule)

            e6_rule.name = '[DEPRECATED] ' + e6_rule.name
            e6_rule.applicable_models.clear()
            e6_rule.save(update_fields=['name'])

    # --- 2. Rename belts rule ---
    belts_rule = MaintenanceRule.objects.filter(name__icontains='ремнів').first()
    if belts_rule and 'E6' in belts_rule.name:
        belts_rule.name = 'Заміна ремнів, роликів Stralis'
        belts_rule.save(update_fields=['name'])

    # --- 3. Merge WorkPrices ---
    base_work = WorkPrice.objects.filter(name='Заміна оливи в двигуні STRALIS').first()
    e6_work = WorkPrice.objects.filter(name='Заміна оливи в двигуні STRALIS E6').first()

    if base_work and e6_work and base_work.pk != e6_work.pk:
        ServiceWork.objects.filter(work=e6_work).update(work=base_work)
        for rule in MaintenanceRule.objects.filter(work=e6_work):
            rule.work = base_work
            rule.save(update_fields=['work'])
        e6_work.name = '[DEPRECATED] ' + e6_work.name
        e6_work.save(update_fields=['name'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0022_deduplicate_kit_filters_unique'),
    ]

    operations = [
        migrations.RunPython(merge_rules, noop),
    ]
