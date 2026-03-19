from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0007_alter_repairphoto_image_alter_serviceorder_car_photo_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='serviceorder',
            name='intervals_snapshot',
            field=models.JSONField(blank=True, editable=False, null=True, verbose_name='Знімок інтервалів до DONE'),
        ),
    ]
