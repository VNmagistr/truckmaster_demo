import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0009_product_barcode'),
        ('orders', '0010_serviceorder_closed_at'),
    ]

    operations = [
        # Розширюємо max_length для service_type (auto_gearbox = 12 символів)
        migrations.AlterField(
            model_name='basemaintenancekitfilter',
            name='service_type',
            field=models.CharField(
                choices=[
                    ('both', 'Повне і часткове ТО'),
                    ('full', 'Тільки повне ТО'),
                    ('partial', 'Тільки часткове ТО'),
                    ('rear_axle', 'Заміна оливи заднього моста'),
                    ('gearbox', 'Заміна оливи КПП'),
                    ('auto_gearbox', 'Заміна оливи АКПП'),
                    ('belts', 'Заміна ремнів/роликів'),
                    ('chains', 'Заміна ланцюгів'),
                ],
                default='both',
                help_text='В якому виді ТО використовується цей фільтр',
                max_length=12,
                verbose_name='Вид ТО',
            ),
        ),
        migrations.AlterField(
            model_name='maintenancekitfilter',
            name='service_type',
            field=models.CharField(
                choices=[
                    ('both', 'Повне і часткове ТО'),
                    ('full', 'Тільки повне ТО'),
                    ('partial', 'Тільки часткове ТО'),
                    ('rear_axle', 'Заміна оливи заднього моста'),
                    ('gearbox', 'Заміна оливи КПП'),
                    ('auto_gearbox', 'Заміна оливи АКПП'),
                    ('belts', 'Заміна ремнів/роликів'),
                    ('chains', 'Заміна ланцюгів'),
                ],
                default='both',
                help_text='В якому виді ТО використовується цей фільтр',
                max_length=12,
                verbose_name='Вид ТО',
            ),
        ),
        # Нові поля оливи в MaintenanceKit
        migrations.AddField(
            model_name='maintenancekit',
            name='rear_axle_oil',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='rear_axle_oil_for_trucks',
                to='inventory.product',
                verbose_name='Олива заднього моста',
            ),
        ),
        migrations.AddField(
            model_name='maintenancekit',
            name='rear_axle_oil_quantity',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='Кількість оливи заднього моста'),
        ),
        migrations.AddField(
            model_name='maintenancekit',
            name='gearbox_oil',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='gearbox_oil_for_trucks',
                to='inventory.product',
                verbose_name='Олива КПП',
            ),
        ),
        migrations.AddField(
            model_name='maintenancekit',
            name='gearbox_oil_quantity',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='Кількість оливи КПП'),
        ),
        migrations.AddField(
            model_name='maintenancekit',
            name='auto_gearbox_oil',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='auto_gearbox_oil_for_trucks',
                to='inventory.product',
                verbose_name='Олива АКПП',
            ),
        ),
        migrations.AddField(
            model_name='maintenancekit',
            name='auto_gearbox_oil_quantity',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='Кількість оливи АКПП'),
        ),
        # Окремі інтервали АКПП в TruckMaintenanceIntervals
        migrations.AddField(
            model_name='truckmaintenanceintervals',
            name='auto_gearbox_oil_interval',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Інтервал заміни оливи АКПП (км)'),
        ),
        migrations.AddField(
            model_name='truckmaintenanceintervals',
            name='auto_gearbox_oil_last_km',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Пробіг при останній заміні оливи АКПП'),
        ),
    ]
