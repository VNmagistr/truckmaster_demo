from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='nova_poshta_declaration',
            field=models.CharField(blank=True, max_length=30, verbose_name='Декларація Нової Пошти'),
        ),
    ]
