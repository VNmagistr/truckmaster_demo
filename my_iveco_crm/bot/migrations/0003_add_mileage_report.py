from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0002_add_driver_role'),
        ('clients', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MileageReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mileage', models.PositiveIntegerField(verbose_name='Пробіг (км)')),
                ('reported_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата введення')),
                ('bot_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.botuser', verbose_name='Користувач')),
                ('truck', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mileage_reports', to='clients.truck', verbose_name='Вантажівка')),
            ],
            options={
                'verbose_name': 'Звіт про пробіг',
                'verbose_name_plural': 'Звіти про пробіг',
                'ordering': ['-reported_at'],
            },
        ),
    ]
