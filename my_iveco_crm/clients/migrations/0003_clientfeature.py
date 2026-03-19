from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0002_client_user_account'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientFeature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cabinet', models.BooleanField(
                    default=True, verbose_name='Особистий кабінет',
                    help_text='Доступ до /cabinet/ — перегляд замовлень та авто.',
                )),
                ('bot', models.BooleanField(
                    default=True, verbose_name='Telegram бот',
                    help_text='Участь у Telegram боті (звіти пробігу, команди).',
                )),
                ('invoices', models.BooleanField(
                    default=True, verbose_name='Рахунки',
                    help_text='Перегляд виставлених рахунків на запчастини.',
                )),
                ('appointments', models.BooleanField(
                    default=True, verbose_name='Онлайн-запис',
                    help_text='Самостійний запис на СТО через кабінет.',
                )),
                ('notifications_telegram', models.BooleanField(
                    default=True, verbose_name='Сповіщення Telegram',
                    help_text='Надсилати Telegram-сповіщення при додаванні фото ремонту.',
                )),
                ('notifications_whatsapp', models.BooleanField(
                    default=True, verbose_name='Сповіщення WhatsApp',
                    help_text='Надсилати WhatsApp-сповіщення при додаванні фото ремонту.',
                )),
                ('client', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='features',
                    to='clients.client',
                    verbose_name='Клієнт',
                )),
            ],
            options={
                'verbose_name': 'Доступ до функцій',
                'verbose_name_plural': 'Доступ до функцій',
            },
        ),
    ]
