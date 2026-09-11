from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0007_truck_transmission_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='notes',
            field=models.TextField(blank=True, default='', verbose_name='Примітки'),
        ),
        migrations.AddField(
            model_name='truck',
            name='notes',
            field=models.TextField(blank=True, default='', verbose_name='Примітки'),
        ),
    ]
