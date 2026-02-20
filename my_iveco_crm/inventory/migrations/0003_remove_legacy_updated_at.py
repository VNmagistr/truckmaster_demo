from django.db import migrations


class Migration(migrations.Migration):
    """
    Видаляє колонку updated_at з inventory_product, яка залишилась від
    старих міграцій (до squash). Поточна модель Product її не має.
    """

    dependencies = [
        ('inventory', '0002_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE inventory_product
                DROP COLUMN IF EXISTS updated_at;
            """,
            reverse_sql="""
                ALTER TABLE inventory_product
                ADD COLUMN updated_at timestamp with time zone;
            """,
        ),
    ]
