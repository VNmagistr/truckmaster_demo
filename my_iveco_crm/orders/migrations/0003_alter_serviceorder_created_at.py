import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_truckmaintenanceintervals'),
    ]

    operations = [
        migrations.AlterField(
            model_name='serviceorder',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Створено'),
        ),
    ]
