from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0009_alter_serviceorder_marked_for_deletion_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='serviceorder',
            name='closed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Закрито'),
        ),
    ]
