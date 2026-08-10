from django.db import migrations


def create_menu_shortlink(apps, schema_editor):
    ShortLink = apps.get_model('shortlinks', 'ShortLink')
    ShortLink.objects.get_or_create(
        slug='menu',
        defaults={
            'target_url': 'https://ital-truck.com.ua/qr',
            'label': 'Меню-візитка для QR-коду',
            'is_active': True,
        },
    )


def remove_menu_shortlink(apps, schema_editor):
    ShortLink = apps.get_model('shortlinks', 'ShortLink')
    ShortLink.objects.filter(slug='menu').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('shortlinks', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_menu_shortlink, remove_menu_shortlink),
    ]
