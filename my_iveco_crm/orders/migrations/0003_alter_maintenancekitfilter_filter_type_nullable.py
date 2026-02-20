from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_add_recommendations_to_serviceorder'),
    ]

    operations = [
        migrations.AlterField(
            model_name='maintenancekitfilter',
            name='filter_type',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='orders.filtertype',
                verbose_name='Тип фільтра',
            ),
        ),
    ]
