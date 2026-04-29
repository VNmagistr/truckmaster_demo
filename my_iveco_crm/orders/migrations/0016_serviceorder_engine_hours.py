from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0015_servicework_custom_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='serviceorder',
            name='engine_hours',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text='Заповнюється для моделей зі спецтехнікою (напр. Trakker)',
                verbose_name='Мотогодини',
            ),
        ),
    ]
