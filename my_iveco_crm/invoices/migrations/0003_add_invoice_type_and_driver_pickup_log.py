import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
        ('inventory', '0001_initial'),
        ('invoices', '0002_add_nova_poshta_declaration'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='invoice_type',
            field=models.CharField(
                choices=[('delivery', 'НП / Самовивіз'), ('driver_tab', 'Видача водію')],
                default='delivery',
                max_length=20,
                verbose_name='Тип рахунку',
            ),
        ),
        migrations.CreateModel(
            name='DriverPickupLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.localdate, verbose_name='Дата')),
                ('description', models.CharField(max_length=255, verbose_name='Опис')),
                ('quantity', models.DecimalField(decimal_places=2, default=1, max_digits=10, verbose_name='Кількість')),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Ціна за одиницю')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='driver_pickups',
                    to='clients.client',
                    verbose_name='Клієнт',
                )),
                ('truck', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='driver_pickups',
                    to='clients.truck',
                    verbose_name='Вантажівка',
                )),
                ('product', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='driver_pickups',
                    to='inventory.product',
                    verbose_name='Товар',
                )),
                ('invoice', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='pickup_logs',
                    to='invoices.invoice',
                    verbose_name='Рахунок',
                )),
            ],
            options={
                'verbose_name': 'Видача водію',
                'verbose_name_plural': 'Видачі водієм',
                'ordering': ['-date', '-created_at'],
            },
        ),
    ]
