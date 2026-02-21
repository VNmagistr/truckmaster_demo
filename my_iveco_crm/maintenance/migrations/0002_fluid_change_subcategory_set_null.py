from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0001_initial'),
        ('inventory', '0003_remove_legacy_updated_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fluidchangerecord',
            name='subcategory',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='inventory.subcategory',
                verbose_name='Тип рідини/оливи',
            ),
        ),
    ]
