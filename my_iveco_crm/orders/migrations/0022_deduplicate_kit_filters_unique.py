from django.db import migrations


def deduplicate_kit_filters(apps, schema_editor):
    """Remove duplicate MaintenanceKitFilter entries (same kit + part)."""
    MaintenanceKitFilter = apps.get_model('orders', 'MaintenanceKitFilter')
    seen = set()
    to_delete = []
    for f in MaintenanceKitFilter.objects.order_by('id'):
        key = (f.maintenance_kit_id, f.part_id)
        if key in seen:
            to_delete.append(f.pk)
        else:
            seen.add(key)
    if to_delete:
        MaintenanceKitFilter.objects.filter(pk__in=to_delete).delete()


def deduplicate_template_filters(apps, schema_editor):
    """Remove duplicate TemplateKitFilter entries (same template + part)."""
    TemplateKitFilter = apps.get_model('orders', 'TemplateKitFilter')
    seen = set()
    to_delete = []
    for f in TemplateKitFilter.objects.order_by('id'):
        key = (f.template_id, f.part_id)
        if key in seen:
            to_delete.append(f.pk)
        else:
            seen.add(key)
    if to_delete:
        TemplateKitFilter.objects.filter(pk__in=to_delete).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0021_maintenance_rule_work_fk'),
    ]

    operations = [
        migrations.RunPython(deduplicate_kit_filters, migrations.RunPython.noop),
        migrations.RunPython(deduplicate_template_filters, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='maintenancekitfilter',
            unique_together={('maintenance_kit', 'part')},
        ),
        migrations.AlterUniqueTogether(
            name='templatekitfilter',
            unique_together={('template', 'part')},
        ),
    ]
