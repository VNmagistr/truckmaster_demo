from django.db import migrations


class Migration(migrations.Migration):
    """
    В БД існують дві таблиці категорій:
    - inventory_productcategory (стара назва, реальні дані, на неї посилаються підкатегорії)
    - inventory_category (порожня, яку Django вважав активною через CreateModel замість RenameModel)

    Вирішення: вказуємо Category.Meta.db_table = 'inventory_productcategory'.
    Це тільки зміна стану Django — жодних DDL-операцій не потрібно.
    """

    dependencies = [
        ('inventory', '0006_subcategory_sort_order'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],  # нічого не змінюємо в БД
            state_operations=[
                migrations.AlterModelTable(
                    name='category',
                    table='inventory_productcategory',
                ),
            ],
        ),
    ]
