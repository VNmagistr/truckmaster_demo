from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Змінює дефолти ClientFeature: тільки cabinet=True за замовчуванням.
    Решта фічей вимкнені для нових клієнтів поки адміністратор не увімкне.
    """

    dependencies = [
        ('clients', '0003_clientfeature'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clientfeature',
            name='bot',
            field=models.BooleanField(
                default=False, verbose_name='Telegram бот',
                help_text='Участь у Telegram боті (звіти пробігу, команди).',
            ),
        ),
        migrations.AlterField(
            model_name='clientfeature',
            name='invoices',
            field=models.BooleanField(
                default=False, verbose_name='Рахунки',
                help_text='Перегляд виставлених рахунків на запчастини.',
            ),
        ),
        migrations.AlterField(
            model_name='clientfeature',
            name='appointments',
            field=models.BooleanField(
                default=False, verbose_name='Онлайн-запис',
                help_text='Самостійний запис на СТО через кабінет.',
            ),
        ),
        migrations.AlterField(
            model_name='clientfeature',
            name='notifications_telegram',
            field=models.BooleanField(
                default=False, verbose_name='Сповіщення Telegram',
                help_text='Надсилати Telegram-сповіщення при додаванні фото ремонту.',
            ),
        ),
        migrations.AlterField(
            model_name='clientfeature',
            name='notifications_whatsapp',
            field=models.BooleanField(
                default=False, verbose_name='Сповіщення WhatsApp',
                help_text='Надсилати WhatsApp-сповіщення при додаванні фото ремонту.',
            ),
        ),
    ]
