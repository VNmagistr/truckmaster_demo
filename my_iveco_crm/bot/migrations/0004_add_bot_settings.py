from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0003_add_mileage_report'),
    ]

    operations = [
        migrations.CreateModel(
            name='BotSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ask_mileage_enabled', models.BooleanField(
                    default=False,
                    verbose_name='Щотижневий запит пробігу',
                    help_text='Щопонеділка о 10:00 власникам надсилається запит на введення поточного пробігу.'
                )),
            ],
            options={
                'verbose_name': 'Налаштування бота',
                'verbose_name_plural': 'Налаштування бота',
            },
        ),
    ]
