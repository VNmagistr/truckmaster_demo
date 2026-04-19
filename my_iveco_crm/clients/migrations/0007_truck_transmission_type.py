from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0006_client_email_verified'),
    ]

    operations = [
        migrations.AddField(
            model_name='truck',
            name='transmission_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('manual', 'Механічна'),
                    ('automatic', 'Автоматична'),
                    ('robotic', 'Роботизована'),
                ],
                max_length=10,
                null=True,
                verbose_name='Тип КПП',
            ),
        ),
    ]
