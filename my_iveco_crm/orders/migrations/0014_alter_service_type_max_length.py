from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0013_maintenancekit_auto_gearbox_filter'),
    ]

    operations = [
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
                    ('auto_gearbox_filter', 'Заміна фільтра АКПП'),
                    ('belts', 'Заміна ремнів/роликів'),
                    ('chains', 'Заміна ланцюгів'),
                ],
                default='both',
                max_length=20,
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
                    ('auto_gearbox_filter', 'Заміна фільтра АКПП'),
                    ('belts', 'Заміна ремнів/роликів'),
                    ('chains', 'Заміна ланцюгів'),
                ],
                default='both',
                max_length=20,
                verbose_name='Вид ТО',
            ),
        ),
    ]
