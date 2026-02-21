from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Стовпець description вже існує в БД (inventory_subcategory) як NOT NULL без default.
    Виконуємо два кроки:
    1. database_operations: встановлюємо default '' та заповнюємо NULL-значення
    2. state_operations: синхронізуємо Python-модель з реальною схемою БД
    """

    dependencies = [
        ('inventory', '0004_drop_product_category_column'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="UPDATE inventory_subcategory SET description = '' WHERE description IS NULL;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql="ALTER TABLE inventory_subcategory ALTER COLUMN description SET DEFAULT '';",
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='subcategory',
                    name='description',
                    field=models.TextField(blank=True, default='', verbose_name='Опис'),
                    preserve_default=True,
                ),
            ],
        ),
    ]
