from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0007_orderitem_received'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='purchase_price',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10,
                null=True, verbose_name='Ціна закупівлі'
            ),
        ),
    ]
