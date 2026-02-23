from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Category(models.Model):
    """Категорія товарів (Оливи, Фільтри, тощо)"""
    name = models.CharField('Назва', max_length=100)
    slug = models.SlugField('Slug', unique=True)
    category_type = models.CharField('Тип', max_length=50, default='other')
    is_active = models.BooleanField('Активна', default=True)
    sort_order = models.IntegerField('Порядок сортування', default=0)

    class Meta:
        verbose_name = 'Категорія'
        verbose_name_plural = 'Категорії'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    """Підкатегорія товарів"""
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories',
        verbose_name='Категорія'
    )
    name = models.CharField('Назва', max_length=100)
    slug = models.SlugField('Slug')
    is_active = models.BooleanField('Активна', default=True)
    default_change_interval_km = models.PositiveIntegerField(
        'Інтервал заміни (км)', null=True, blank=True
    )

    class Meta:
        verbose_name = 'Підкатегорія'
        verbose_name_plural = 'Підкатегорії'
        ordering = ['category', 'name']
        unique_together = ['category', 'slug']

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    """Склад"""
    name = models.CharField('Назва', max_length=100)
    slug = models.SlugField('Slug', unique=True)
    address = models.TextField('Адреса', blank=True)
    is_active = models.BooleanField('Активний', default=True)
    is_default = models.BooleanField('За замовчуванням', default=False)
    sort_order = models.IntegerField('Порядок сортування', default=0)

    class Meta:
        verbose_name = 'Склад'
        verbose_name_plural = 'Склади'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while Warehouse.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        if self.is_default:
            Warehouse.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Product(models.Model):
    """Товар / Запчастина"""
    UNIT_CHOICES = [
        ('pcs', 'шт'),
        ('l', 'л'),
        ('kg', 'кг'),
        ('pack', 'уп'),
        ('m', 'м'),
    ]

    sku_code = models.CharField('Артикул', max_length=100, unique=True)
    name = models.CharField('Назва', max_length=255)
    brand = models.CharField('Бренд', max_length=100, blank=True)
    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Підкатегорія'
    )

    cost_price = models.DecimalField('Собівартість', max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField('Ціна продажу', max_digits=10, decimal_places=2, default=0)
    current_stock = models.DecimalField('Залишок', max_digits=10, decimal_places=2, default=0)
    min_stock_level = models.DecimalField('Мін. залишок', max_digits=10, decimal_places=2, default=0)

    unit = models.CharField('Одиниця виміру', max_length=10, choices=UNIT_CHOICES, default='pcs')
    is_active = models.BooleanField('Активний', default=True)
    created_at = models.DateTimeField('Створено', auto_now_add=True)

    viscosity = models.CharField('В\'язкість', max_length=20, blank=True)
    volume_per_unit = models.DecimalField('Об\'єм в упаковці', max_digits=10, decimal_places=2, null=True, blank=True)
    specifications = models.TextField('Специфікації', blank=True)
    notes = models.TextField('Примітки', blank=True)
    address_in_stock = models.CharField('Адреса на складі', max_length=100, blank=True)

    marked_for_deletion = models.BooleanField('Позначено на видалення', default=False)
    deletion_reason = models.TextField('Причина видалення', blank=True)
    marked_for_deletion_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products_marked_for_deletion',
        verbose_name='Позначив на видалення'
    )
    marked_for_deletion_at = models.DateTimeField('Дата позначення', null=True, blank=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товари'
        ordering = ['name']

    def __str__(self):
        parts = [self.name]
        if self.brand:
            parts.insert(0, self.brand)
        if self.viscosity:
            parts.append(self.viscosity)
        return f'[{self.sku_code}] {" ".join(parts)}'

    @property
    def is_low_stock(self):
        return self.current_stock <= self.min_stock_level


class StockItem(models.Model):
    """Залишок товару на конкретному складі"""
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='stock_items',
        verbose_name='Склад'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_items',
        verbose_name='Товар'
    )
    quantity = models.DecimalField('Кількість', max_digits=12, decimal_places=2, default=0)
    reserved = models.DecimalField('Зарезервовано', max_digits=12, decimal_places=2, default=0)
    location = models.CharField('Місце зберігання', max_length=100, blank=True)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)

    class Meta:
        verbose_name = 'Залишок на складі'
        verbose_name_plural = 'Залишки на складі'
        unique_together = ['warehouse', 'product']

    def __str__(self):
        return f"{self.product} @ {self.warehouse}: {self.quantity}"

    @property
    def available(self):
        return self.quantity - self.reserved


class StockMovement(models.Model):
    """Рух товару по складу"""
    MOVEMENT_TYPES = [
        ('in', 'Надходження'),
        ('out', 'Витрата'),
        ('transfer', 'Переміщення'),
        ('adjustment', 'Інвентаризація'),
        ('return', 'Повернення'),
        ('write_off', 'Списання'),
    ]

    movement_type = models.CharField('Тип руху', max_length=20, choices=MOVEMENT_TYPES)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name='Товар'
    )
    quantity = models.DecimalField('Кількість', max_digits=12, decimal_places=2)
    warehouse_from = models.ForeignKey(
        Warehouse,
        related_name='out_movements',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Зі складу'
    )
    warehouse_to = models.ForeignKey(
        Warehouse,
        related_name='in_movements',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='На склад'
    )
    created_at = models.DateTimeField('Створено', auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_movements',
        verbose_name='Створив'
    )
    service_order = models.ForeignKey(
        'orders.ServiceOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Наряд-замовлення'
    )
    supplier = models.CharField('Постачальник', max_length=200, blank=True)
    invoice_number = models.CharField('Номер накладної', max_length=100, blank=True)
    purchase_price = models.DecimalField('Закупівельна ціна', max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField('Примітки', blank=True)

    class Meta:
        verbose_name = 'Рух товару'
        verbose_name_plural = 'Рух товарів'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()}: {self.product} ({self.quantity})"


class UsedPart(models.Model):
    """Використана запчастина"""
    service_work = models.ForeignKey(
        'orders.ServiceWork',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='used_parts',
        verbose_name='Робота'
    )
    service_order = models.ForeignKey(
        'orders.ServiceOrder',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='direct_parts',
        verbose_name='Наряд-замовлення'
    )
    part = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name='Запчастина'
    )
    quantity = models.DecimalField('Кількість', max_digits=10, decimal_places=2)
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Склад'
    )
    unit_price = models.DecimalField('Ціна за одиницю', max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = 'Використана запчастина'
        verbose_name_plural = 'Використані запчастини'
        ordering = ['part__name']

    def __str__(self):
        return f"{self.part.name} x {self.quantity}"

    def save(self, *args, **kwargs):
        if self.unit_price is None and self.part:
            self.unit_price = self.part.selling_price
        super().save(*args, **kwargs)

    @property
    def total_price(self):
        if self.unit_price:
            return self.quantity * self.unit_price
        return self.quantity * (self.part.selling_price or 0)
