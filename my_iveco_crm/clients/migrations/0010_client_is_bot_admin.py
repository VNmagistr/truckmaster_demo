# clients/migrations/0009_client_is_bot_admin.py
# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0008_alter_truck_last_seven_vin'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='is_bot_admin',
            field=models.BooleanField(
                default=False, 
                verbose_name='Адміністратор Telegram бота',
                help_text='Чи має цей клієнт доступ до адміністраторських функцій бота'
            ),
        ),
    ]




