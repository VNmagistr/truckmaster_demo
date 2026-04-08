from django.db import migrations, models


def set_existing_clients_verified(apps, schema_editor):
    """Existing clients are considered verified — they predate the verification feature."""
    Client = apps.get_model('clients', 'Client')
    Client.objects.all().update(email_verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0005_alter_client_marked_for_deletion_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='email_verified',
            field=models.BooleanField(default=False, verbose_name='Email верифіковано'),
        ),
        migrations.RunPython(set_existing_clients_verified, migrations.RunPython.noop),
    ]
