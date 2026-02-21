from django.db import migrations


class Migration(migrations.Migration):
    """
    Видаляє застарілий стовпець category_id з таблиці inventory_product.
    Цей стовпець залишився від старої моделі Part, яка мала пряме FK до Category.
    Зараз Product використовує SubCategory (не Category напряму),
    тому стовпець є зайвим і блокує видалення категорій.
    """

    dependencies = [
        ('inventory', '0003_remove_legacy_updated_at'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE inventory_product DROP COLUMN IF EXISTS category_id;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
