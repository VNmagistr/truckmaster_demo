# orders/migrations/0022_remove_workprice_price_field.py
# Generated manually on 2025-11-30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0021_alter_filtertype_replacement_interval_km'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='workprice',
            name='price',
        ),
    ]
