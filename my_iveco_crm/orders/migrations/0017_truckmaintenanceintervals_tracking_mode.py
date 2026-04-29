from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0016_serviceorder_engine_hours'),
    ]

    operations = [
        migrations.AddField(
            model_name='truckmaintenanceintervals',
            name='tracking_mode',
            field=models.CharField(
                choices=[('mileage', 'По кілометражу'), ('engine_hours', 'По мотогодинах')],
                default='mileage',
                max_length=20,
                help_text='Для спецтехніки (Trakker) можна вести облік у мотогодинах. '
                          'У режимі engine_hours поля *_interval/*_last_km інтерпретуються як години.',
                verbose_name='Режим обліку',
            ),
        ),
    ]
