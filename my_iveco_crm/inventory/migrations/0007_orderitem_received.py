import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0006_add_orderfolder_archive'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='is_received',
            field=models.BooleanField(default=False, verbose_name='Отримано'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='received_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Отримано о'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='received_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='received_items',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Отримав',
            ),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='linked_product',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='order_items',
                to='inventory.product',
                verbose_name='Товар на складі',
            ),
        ),
    ]
