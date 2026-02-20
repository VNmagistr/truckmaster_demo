from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0002_fix_truck_license_plate_index'),
    ]

    operations = [
        migrations.AlterField(
            model_name='truck',
            name='last_seven_vin',
            field=models.CharField(db_index=True, editable=False, max_length=7, verbose_name='Останні 7 символів VIN'),
        ),
    ]
