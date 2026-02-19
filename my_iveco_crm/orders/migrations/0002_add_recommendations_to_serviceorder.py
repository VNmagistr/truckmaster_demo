from django.db import migrations


def add_recommendations_column(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(
            "ALTER TABLE orders_serviceorder "
            "ADD COLUMN IF NOT EXISTS recommendations TEXT NOT NULL DEFAULT '';"
        )
    else:
        # SQLite: перевіряємо вручну
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(orders_serviceorder)")
            columns = [row[1] for row in cursor.fetchall()]
        if 'recommendations' not in columns:
            schema_editor.execute(
                "ALTER TABLE orders_serviceorder "
                "ADD COLUMN recommendations TEXT NOT NULL DEFAULT '';"
            )


def remove_recommendations_column(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(
            "ALTER TABLE orders_serviceorder DROP COLUMN IF EXISTS recommendations;"
        )


class Migration(migrations.Migration):
    """
    Додає колонку recommendations до orders_serviceorder.
    Колонка є в моделі та 0001_initial, але відсутня в БД
    через fake-apply міграції на старій схемі.
    """

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            add_recommendations_column,
            reverse_code=remove_recommendations_column,
        ),
    ]
