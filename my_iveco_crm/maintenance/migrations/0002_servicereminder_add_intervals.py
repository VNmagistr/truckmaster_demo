from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicereminder',
            name='interval_km',
            field=models.PositiveIntegerField(
                blank=True, null=True,
                verbose_name='Інтервал за пробігом (км)',
                help_text='Через скільки км створювати наступне нагадування. Порожньо — з типу ТО.'
            ),
        ),
        migrations.AddField(
            model_name='servicereminder',
            name='interval_months',
            field=models.PositiveIntegerField(
                blank=True, null=True,
                verbose_name='Інтервал за часом (місяців)',
                help_text='Через скільки місяців створювати наступне нагадування. Порожньо — з типу ТО.'
            ),
        ),
    ]
