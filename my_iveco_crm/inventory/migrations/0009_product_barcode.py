from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0008_orderitem_purchase_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='barcode',
            field=models.CharField(blank=True, db_index=True, max_length=100, verbose_name='Штрих-код'),
        ),
    ]
