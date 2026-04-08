import cabinet.models
import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('clients', '0006_client_email_verified'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailVerification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ('email', models.EmailField(max_length=254, verbose_name='Email')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(default=cabinet.models._default_expiry)),
                ('is_used', models.BooleanField(default=False)),
                ('client', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='email_verifications',
                    to='clients.client',
                    verbose_name='Клієнт',
                )),
            ],
            options={
                'verbose_name': 'Email верифікація',
                'verbose_name_plural': 'Email верифікації',
                'ordering': ['-created_at'],
            },
        ),
    ]
