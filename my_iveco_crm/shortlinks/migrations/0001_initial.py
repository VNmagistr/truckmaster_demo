from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ShortLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(help_text="Частина URL після /go/ (напр. 'maps', 'bot', 'review').", max_length=64, unique=True)),
                ('target_url', models.URLField(help_text='Куди редіректить (напр. посилання на Google Maps, Telegram-бот).', max_length=2048)),
                ('label', models.CharField(blank=True, help_text='Опис для адмінки (не показується користувачу).', max_length=200)),
                ('is_active', models.BooleanField(default=True)),
                ('hits', models.PositiveIntegerField(default=0, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Коротке посилання',
                'verbose_name_plural': 'Короткі посилання',
                'ordering': ['slug'],
            },
        ),
    ]
