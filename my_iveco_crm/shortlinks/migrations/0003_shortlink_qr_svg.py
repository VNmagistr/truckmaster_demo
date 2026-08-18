from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shortlinks', '0002_create_menu_shortlink'),
    ]

    operations = [
        migrations.AddField(
            model_name='shortlink',
            name='qr_svg',
            field=models.TextField(
                blank=True,
                default='',
                editable=False,
                verbose_name='QR-код (SVG)',
            ),
        ),
        migrations.AlterModelOptions(
            name='shortlink',
            options={
                'ordering': ['slug'],
                'verbose_name': 'QR-код',
                'verbose_name_plural': 'QR-коди',
            },
        ),
    ]
