from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0007_truck_transmission_type'),
        ('orders', '0017_truckmaintenanceintervals_tracking_mode'),
    ]

    operations = [
        migrations.CreateModel(
            name='MaintenanceIntervalsTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('euro_standard', models.CharField(blank=True, default='', help_text='Залиште порожнім, щоб еталон підходив до будь-якого євростандарту', max_length=10, verbose_name='Євростандарт')),
                ('transmission_type', models.CharField(blank=True, default='', help_text='Залиште порожнім, щоб еталон підходив до будь-якої КПП', max_length=10, verbose_name='Тип КПП')),
                ('tracking_mode', models.CharField(choices=[('mileage', 'По кілометражу'), ('engine_hours', 'По мотогодинах')], default='mileage', max_length=20, verbose_name='Режим обліку')),
                ('engine_oil_interval', models.PositiveIntegerField(blank=True, null=True, verbose_name='Інтервал заміни оливи двигуна')),
                ('gearbox_oil_interval', models.PositiveIntegerField(blank=True, null=True, verbose_name='Інтервал заміни оливи КПП')),
                ('auto_gearbox_oil_interval', models.PositiveIntegerField(blank=True, null=True, verbose_name='Інтервал заміни оливи АКПП')),
                ('auto_gearbox_filter_interval', models.PositiveIntegerField(blank=True, null=True, verbose_name='Інтервал заміни фільтра АКПП')),
                ('rear_axle_oil_interval', models.PositiveIntegerField(blank=True, null=True, verbose_name='Інтервал заміни оливи заднього моста')),
                ('belts_interval', models.PositiveIntegerField(blank=True, null=True, verbose_name='Інтервал заміни ремнів/роликів')),
                ('chains_interval', models.PositiveIntegerField(blank=True, null=True, verbose_name='Інтервал заміни ланцюгів')),
                ('notes', models.CharField(blank=True, default='', max_length=255, verbose_name='Нотатка')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('base_model', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='interval_templates',
                    to='clients.ivecobasemodel',
                    verbose_name='Базова модель',
                )),
            ],
            options={
                'verbose_name': 'Еталон регламенту ТО',
                'verbose_name_plural': 'Еталони регламенту ТО',
                'ordering': ['base_model__name', 'euro_standard', 'transmission_type'],
            },
        ),
        migrations.AddConstraint(
            model_name='maintenanceintervalstemplate',
            constraint=models.UniqueConstraint(
                fields=('base_model', 'euro_standard', 'transmission_type'),
                name='uniq_template_per_combo',
            ),
        ),
    ]
