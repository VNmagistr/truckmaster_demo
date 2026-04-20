import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0009_product_barcode'),
        ('orders', '0012_truckmaintenanceintervals_auto_gearbox_filter'),
    ]

    operations = [
        migrations.AddField(
            model_name='maintenancekit',
            name='auto_gearbox_filter',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='auto_gearbox_filter_for_trucks',
                to='inventory.product',
                verbose_name='Фільтр АКПП',
            ),
        ),
        migrations.AddField(
            model_name='maintenancekit',
            name='auto_gearbox_filter_quantity',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Кількість фільтрів АКПП'),
        ),
    ]
