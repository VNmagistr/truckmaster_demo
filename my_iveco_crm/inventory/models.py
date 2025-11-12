from django.db import models

# 1. Модель Категорій (без змін)
class PartCategory(models.Model):
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, 
        blank=True, 
        related_name='subcategories',
        verbose_name="Батьківська категорія"
    )
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва категорії")
    description = models.TextField(blank=True, null=True, verbose_name="Опис")

    class Meta:
        verbose_name = "Категорія запчастин"
        verbose_name_plural = "Категорії запчастин"
        ordering = ['parent__name', 'name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name

# 2. Модель Запчастин (ОНОВЛЕНО)
class Part(models.Model):
    category = models.ForeignKey(
        PartCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Категорія"
    )
    name = models.CharField(max_length=255, verbose_name="Назва запчастини")
    sku_code = models.CharField(max_length=100, unique=True, verbose_name="Код/Артикул")
    description = models.TextField(blank=True, null=True, verbose_name="Опис")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Собівартість")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна продажу")
    current_stock = models.PositiveIntegerField(default=0, verbose_name="Залишок на складі")
    
    substitutes = models.ManyToManyField(
        'self',
        blank=True, 
        symmetrical=False,
        verbose_name="Замінники (аналоги)"
    )

    # 👇 ДОДАЙТЕ ЦІ ДВА ПОЛЯ 👇
    address_in_stock = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Адреса на складі (Полиця, Секція)"
    )
    notes = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Примітки"
    )

    class Meta:
        verbose_name = "Запчастина"
        verbose_name_plural = "Запчастини"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku_code})"

# 3. Модель Використаних Запчастин (без змін)
class UsedPart(models.Model):
    service_work = models.ForeignKey(
        'orders.ServiceWork', 
        on_delete=models.CASCADE, 
        related_name='used_parts',
        verbose_name="Робота"
    )
    part = models.ForeignKey(
        Part, 
        on_delete=models.PROTECT, 
        verbose_name="Запчастина"
    )
    quantity = models.PositiveIntegerField(verbose_name="Кількість")
    
    class Meta:
        verbose_name = "Використана запчастина"
        verbose_name_plural = "Використані запчастини"
        unique_together = ('service_work', 'part') 

    def __str__(self):
        return f"{self.part.name} - {self.quantity} шт."