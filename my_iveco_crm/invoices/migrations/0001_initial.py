from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('clients', '0002_client_user_account'),
        ('inventory', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(max_length=30, unique=True, verbose_name='Номер рахунку')),
                ('date', models.DateField(default=django.utils.timezone.localdate, verbose_name='Дата')),
                ('status', models.CharField(
                    choices=[('draft', 'Чернетка'), ('sent', 'Виставлено'), ('paid', 'Оплачено'), ('cancelled', 'Скасовано')],
                    default='draft', max_length=20, verbose_name='Статус',
                )),
                ('notes', models.TextField(blank=True, verbose_name='Примітки')),
                ('total', models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=12, verbose_name='Сума')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='invoices', to='clients.client', verbose_name='Клієнт',
                )),
                ('truck', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='invoices', to='clients.truck', verbose_name='Вантажівка',
                )),
            ],
            options={
                'verbose_name': 'Рахунок',
                'verbose_name_plural': 'Рахунки на запчастини',
                'ordering': ['-date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='InvoiceItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=255, verbose_name='Опис')),
                ('quantity', models.DecimalField(decimal_places=2, default=1, max_digits=10, verbose_name='Кількість')),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Ціна за одиницю')),
                ('invoice', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items', to='invoices.invoice', verbose_name='Рахунок',
                )),
                ('product', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='invoice_items', to='inventory.product', verbose_name='Товар',
                )),
            ],
            options={
                'verbose_name': 'Позиція рахунку',
                'verbose_name_plural': 'Позиції рахунку',
                'ordering': ['id'],
            },
        ),
    ]
