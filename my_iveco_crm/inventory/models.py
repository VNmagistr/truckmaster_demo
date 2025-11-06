from django.db import models

# 1. Модель Категорій (без змін)
class PartCategory(models.Model):
    parent = models.ForeignKey(
        'self',  # Вказує на цю ж модель (саму на себе)
        on_delete=models.CASCADE, # При видаленні батька - видалити всіх нащадків
        null=True, 
        blank=True, 
        related_name='subcategories', # Дозволяє легко знаходити підрозділи
        verbose_name="Батьківська категорія"
    )
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва категорії")
    description = models.TextField(blank=True, null=True, verbose_name="Опис")

    class Meta:
        verbose_name = "Категорія запчастин"
        verbose_name_plural = "Категорії запчастин"
        ordering = ['parent__name', 'name'] # Сортуємо спочатку за батьком, потім за назвою

    def __str__(self):
        # Робимо назву в адмінці більш зрозумілою, показуючи ієрархію
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

    # 👇 ДОДАЙТЕ ЦЕ ПОЛЕ 👇
    substitutes = models.ManyToManyField(
        'self',  # Зв'язок "багато-до-багатьох" з цією ж моделлю
        blank=True, 
        symmetrical=False, # Важливо! Якщо А - замінник Б, це не означає, що Б - замінник А
        verbose_name="Замінники (аналоги)"
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