from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0002_servicereminder_add_intervals'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicereminder',
            name='notify_frequency_days',
            field=models.PositiveSmallIntegerField(
                choices=[(1, 'Щодня'), (2, 'Кожні 2 дні'), (3, 'Кожні 3 дні'),
                         (7, 'Раз на тиждень'), (14, 'Раз на 2 тижні')],
                default=7,
                verbose_name='Частота нагадувань',
                help_text='Як часто повторювати повідомлення власнику поки ТО не виконано.'
            ),
        ),
        migrations.AddField(
            model_name='servicereminder',
            name='last_notified_at',
            field=models.DateTimeField(
                blank=True, null=True,
                editable=False,
                verbose_name='Останнє надсилання',
            ),
        ),
    ]
