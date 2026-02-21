from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Синхронізує модель SubCategory з БД: поле description існує в таблиці
    inventory_subcategory як NOT NULL, але було відсутнє в Python-моделі.
    Додаємо його назад з blank=True, default='' щоб уникнути IntegrityError.
    """

    dependencies = [
        ('inventory', '0004_drop_product_category_column'),
    ]

    operations = [
        migrations.AddField(
            model_name='subcategory',
            name='description',
            field=models.TextField(blank=True, default='', verbose_name='Опис'),
            preserve_default=True,
        ),
    ]
