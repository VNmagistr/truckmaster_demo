from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0011_maintenance_kit_oil_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='truckmaintenanceintervals',
            name='auto_gearbox_filter_interval',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Інтервал заміни фільтра АКПП (км)'),
        ),
        migrations.AddField(
            model_name='truckmaintenanceintervals',
            name='auto_gearbox_filter_last_km',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Пробіг при останній заміні фільтра АКПП'),
        ),
    ]
