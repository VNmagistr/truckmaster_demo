from django.db import models

# 1. НАША НОВА МОДЕЛЬ КАТЕГОРІЙ
class PartCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва категорії")
    description = models.TextField(blank=True, null=True, verbose_name="Опис")

    class Meta:
        verbose_name = "Категорія запчастин"
        verbose_name_plural = "Категорії запчастин"
        ordering = ['name']

    def __str__(self):
        return self.name

# 2. ОНОВЛЕНА МОДЕЛЬ ЗАПЧАСТИН (Part)
class Part(models.Model):
    # 👇 ДОДАЄМО ЗВ'ЯЗОК З КАТЕГОРІЄЮ 👇
    category = models.ForeignKey(
        PartCategory, 
        on_delete=models.SET_NULL, # Якщо категорію видалять, запчастина залишиться без категорії
        null=True, 
        blank=True, 
        verbose_name="Категорія"
    )

    name = models.CharField(max_length=255, verbose_name="Назва запчастини")
    sku_code = models.CharField(max_length=100, unique=True, verbose_name="Код/Артикул")
    description = models.TextField(blank=True, null=True, verbose_name="Опис")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Собівартість")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна продажу")
    current_stock = models.PositiveIntegerField(default=0, verbose_name="Залишок на складі")

    class Meta:
        verbose_name = "Запчастина"
        verbose_name_plural = "Запчастини"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku_code})"

# 3. МОДЕЛЬ ВИКОРИСТАНИХ ЗАПЧАСТИН (без змін)
class UsedPart(models.Model):
    service_work = models.ForeignKey(
        'orders.ServiceWork', 
        on_delete=models.CASCADE, 
        related_name='used_parts',
        verbose_name="Робота"
    )
    part = models.ForeignKey(
        Part, 
        on_delete=models.PROTECT, # Захищаємо від видалення, якщо запчастина вже використана
        verbose_name="Запчастина"
    )
    quantity = models.PositiveIntegerField(verbose_name="Кількість")

    class Meta:
        verbose_name = "Використана запчастина"
        verbose_name_plural = "Використані запчастини"
        # Гарантуємо, що не можна додати ту саму запчастину до тієї самої роботи двічі
        unique_together = ('service_work', 'part') 

    def __str__(self):
        return f"{self.part.name} - {self.quantity} шт."