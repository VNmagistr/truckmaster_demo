from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_alter_maintenancekitfilter_filter_type_nullable'),
    ]

    operations = [
        migrations.AddField(
            model_name='maintenancekit',
            name='oil_change_interval_km',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name='Інтервал заміни оливи (км)',
                help_text='Наприклад: 20000',
            ),
        ),
        migrations.AddField(
            model_name='maintenancekitfilter',
            name='change_interval_km',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name='Інтервал заміни (км)',
                help_text='Наприклад: 20000',
            ),
        ),
    ]
