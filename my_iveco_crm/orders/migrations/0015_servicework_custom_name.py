from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0014_alter_service_type_max_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicework',
            name='custom_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Назва роботи в наряді'),
        ),
    ]
