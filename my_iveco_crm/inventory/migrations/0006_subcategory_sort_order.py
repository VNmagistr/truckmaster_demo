from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Стовпець sort_order вже існує в БД (inventory_subcategory) як NOT NULL без default.
    Використовуємо SeparateDatabaseAndState: оновлюємо NULL-значення та встановлюємо default,
    не намагаючись додати стовпець (він вже є).
    """

    dependencies = [
        ('inventory', '0005_subcategory_description'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="UPDATE inventory_subcategory SET sort_order = 0 WHERE sort_order IS NULL;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql="ALTER TABLE inventory_subcategory ALTER COLUMN sort_order SET DEFAULT 0;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='subcategory',
                    name='sort_order',
                    field=models.IntegerField(default=0, verbose_name='Порядок сортування'),
                    preserve_default=True,
                ),
            ],
        ),
    ]
