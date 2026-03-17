from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('appointments', '0001_initial'),
        ('clients', '0002_client_user_account'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='IgnoredVehicle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('license_plate', models.CharField(help_text='Буде збережено у верхньому регістрі без пробілів', max_length=20, unique=True, verbose_name='Держномер')),
                ('reason_type', models.CharField(choices=[('staff', 'Персонал СТО'), ('delivery', 'Доставка запчастин'), ('neighbor', 'Сусідня організація'), ('other', 'Інше')], default='other', max_length=20, verbose_name='Категорія')),
                ('description', models.CharField(blank=True, help_text='Наприклад: Форд Транзит — Автолідер запчастини', max_length=255, verbose_name='Опис')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активний')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Додано')),
                ('added_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Додав')),
            ],
            options={
                'verbose_name': 'Ігнорований автомобіль',
                'verbose_name_plural': 'Список ігнору',
                'ordering': ['reason_type', 'license_plate'],
            },
        ),
        migrations.CreateModel(
            name='VehicleArrival',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('license_plate', models.CharField(max_length=20, verbose_name='Розпізнаний номер')),
                ('detected_at', models.DateTimeField(auto_now_add=True, verbose_name='Час заїзду')),
                ('camera_id', models.CharField(blank=True, max_length=100, verbose_name='ID камери')),
                ('confidence', models.FloatField(blank=True, null=True, verbose_name='Впевненість (%)')),
                ('ignored', models.BooleanField(default=False, verbose_name='Ігнорований')),
                ('ignore_reason', models.CharField(blank=True, max_length=100, verbose_name='Причина ігнору')),
                ('notified', models.BooleanField(default=False, verbose_name='Сповіщення надіслано')),
                ('appointment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='arrivals', to='appointments.appointment', verbose_name='Запис на СТО')),
                ('client', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='arrivals', to='clients.client', verbose_name='Клієнт')),
                ('truck', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='arrivals', to='clients.truck', verbose_name='Автомобіль')),
            ],
            options={
                'verbose_name': 'Заїзд автомобіля',
                'verbose_name_plural': 'Журнал заїздів',
                'ordering': ['-detected_at'],
            },
        ),
        migrations.AddIndex(
            model_name='vehiclearrival',
            index=models.Index(fields=['license_plate'], name='alpr_vehicl_license_idx'),
        ),
        migrations.AddIndex(
            model_name='vehiclearrival',
            index=models.Index(fields=['detected_at'], name='alpr_vehicl_detecte_idx'),
        ),
    ]
