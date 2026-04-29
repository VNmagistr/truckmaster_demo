from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0004_add_bot_settings'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnknownPlateSearch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plate', models.CharField(max_length=32, unique=True, verbose_name='Номерний знак')),
                ('search_count', models.PositiveIntegerField(default=1, verbose_name='К-ть пошуків')),
                ('first_searched_at', models.DateTimeField(auto_now_add=True, verbose_name='Перший пошук')),
                ('last_searched_at', models.DateTimeField(auto_now=True, verbose_name='Останній пошук')),
                ('notes', models.CharField(blank=True, max_length=255, verbose_name='Нотатка')),
                ('last_searched_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='unknown_plate_searches',
                    to='bot.botuser',
                    verbose_name='Хто шукав останнім',
                )),
            ],
            options={
                'verbose_name': 'Невідомий номер',
                'verbose_name_plural': 'Невідомі номери',
                'ordering': ['-last_searched_at'],
            },
        ),
    ]
