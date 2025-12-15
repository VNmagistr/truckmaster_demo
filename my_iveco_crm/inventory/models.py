from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class ProductCategory(models.Model):
    """
    Головні категорії товарів
    Приклади: Оливи, Фільтри, Рідини, Омивачі, Запчастини
    """
    CATEGORY_TYPES = [
        ('oil', 'Оливи'),
        ('filter', 'Фільтри'),
        ('fluid', 'Технічні рідини'),
        ('washer', 'Омивачі'),
        ('part', 'Запчастини'),
        ('other', 'Інше'),
    ]
    
    name = models.CharField('Назва', max_length=100)
    slug = models.SlugField('Slug', unique=True)
    category_type = models.CharField(
        'Тип категорії',
        max_length=20,
        choices=CATEGORY_TYPES,
        default='other'
    )
    icon = models.CharField('Іконка', max_length=50, blank=True)
    sort_order = models.IntegerField('Порядок сортування', default=0)
    is_active = models.BooleanField('Активна', default=True)

    class Meta:
        verbose_name = 'Категорія товарів'
        verbose_name_plural = 'Категорії товарів'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class ProductSubcategory(models.Model):
    """
    Підкатегорії товарів
    Приклади для "Оливи": Моторна, Трансмісійна, Гідравлічна, тощо
    """
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.CASCADE,
        related_name='subcategories',
        verbose_name='Категорія'
    )
    name = models.CharField('Назва', max_length=100)
    slug = models.SlugField('Slug')
    description = models.TextField('Опис', blank=True)
    sort_order = models.IntegerField('Порядок сортування', default=0)
    is_active = models.BooleanField('Активна', default=True)
    
    # Інтервал заміни за замовчуванням (для олив та фільтрів)
    default_change_interval_km = models.PositiveIntegerField(
        'Інтервал заміни (км)',
        null=True, blank=True,
        help_text='Стандартний інтервал заміни для цього типу'
    )

    class Meta:
        verbose_name = 'Підкатегорія товарів'
        verbose_name_plural = 'Підкатегорії товарів'
        ordering = ['category', 'sort_order', 'name']
        unique_together = ['category', 'slug']

    def __str__(self):
        return f"{self.category.name} → {self.name}"


class Warehouse(models.Model):
    """
    Склад
    """
    name = models.CharField('Назва', max_length=100)
    slug = models.SlugField('Slug', unique=True)
    address = models.TextField('Адреса', blank=True)
    description = models.TextField('Опис', blank=True)
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
        if self.is_default:
            Warehouse.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class PartCategory(models.Model):
    """Існуюча модель категорій запчастин - залишаємо для сумісності"""
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


class Part(models.Model):
    """
    Товар / Запчастина
    Об'єднує старий функціонал Part з новим функціоналом для олив
    """
    UNIT_CHOICES = [
        ('pcs', 'шт'),
        ('l', 'л'),
        ('kg', 'кг'),
        ('pack', 'уп'),
        ('m', 'м'),
    ]

    category = models.ForeignKey(
        PartCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Категорія (стара)",
        help_text="Застаріле поле, використовуйте subcategory"
    )
    name = models.CharField(max_length=255, verbose_name="Назва")
    sku_code = models.CharField(max_length=100, unique=True, verbose_name="Код/Артикул")
    description = models.TextField(blank=True, null=True, verbose_name="Опис")
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0,
        verbose_name="Собівартість"
    )
    selling_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0,
        verbose_name="Ціна продажу"
    )
 
    current_stock = models.PositiveIntegerField(default=0, verbose_name="Залишок (заг.)")
    
    substitutes = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        verbose_name="Замінники (аналоги)"
    )
    address_in_stock = models.CharField(
        max_length=255,
        blank=True, null=True,
        verbose_name="Адреса на складі"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Примітки")

    subcategory = models.ForeignKey(
        ProductSubcategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='products',
        verbose_name='Підкатегорія (нова)'
    )
    brand = models.CharField('Бренд', max_length=100, blank=True)
    
    viscosity = models.CharField('В\'язкість', max_length=20, blank=True)
    specifications = models.TextField('Специфікації', blank=True)

    unit = models.CharField(
        'Одиниця виміру',
        max_length=10,
        choices=UNIT_CHOICES,
        default='pcs'
    )
    volume_per_unit = models.DecimalField(
        'Об\'єм в упаковці',
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text='Наприклад: 20 літрів в каністрі'
    )
    price_per_liter = models.DecimalField(
        'Ціна за літр',
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    
    min_stock_level = models.DecimalField(
        'Мінімальний залишок',
        max_digits=10, decimal_places=2,
        default=0,
        help_text='Сповіщення коли залишок нижче цього значення'
    )
    
    is_active = models.BooleanField('Активний', default=True)
    created_at = models.DateTimeField('Створено', auto_now_add=True)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)

    class Meta:
        verbose_name = "Товар/Запчастина"
        verbose_name_plural = "Товари/Запчастини"
        ordering = ['name']

    def __str__(self):
        parts = [self.name]
        if self.brand:
            parts.insert(0, self.brand)
        if self.viscosity:
            parts.append(self.viscosity)
        return ' '.join(parts)

    def save(self, *args, **kwargs):
        if self.volume_per_unit and self.volume_per_unit > 0 and self.selling_price:
            self.price_per_liter = self.selling_price / self.volume_per_unit
        super().save(*args, **kwargs)

    def update_current_stock(self):
        """Синхронізує загальний залишок з усіх складів"""
        total = self.stock_items.aggregate(
            total=Sum('quantity')
        )['total'] or 0
        
        if self.current_stock != total:
            Part.objects.filter(pk=self.pk).update(current_stock=total)
    
    @property
    def total_stock(self):
        """Використовує кешоване значення"""
        return self.current_stock

    @property
    def is_oil(self):
        """Чи є цей товар оливою"""
        return self.subcategory and self.subcategory.category.category_type == 'oil'

    @property
    def is_filter(self):
        """Чи є цей товар фільтром"""
        return self.subcategory and self.subcategory.category.category_type == 'filter'

    @property
    def total_stock(self):
        """Загальний залишок по всіх складах"""
        return self.stock_items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0


class Stock(models.Model):
    """
    Залишки товару на конкретному складі
    """
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='stock_items',
        verbose_name='Склад'
    )
    product = models.ForeignKey(
        Part,
        on_delete=models.CASCADE,
        related_name='stock_items',
        verbose_name='Товар'
    )
    
    quantity = models.DecimalField(
        'Кількість',
        max_digits=12, decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    reserved = models.DecimalField(
        'Зарезервовано',
        max_digits=12, decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Розташування на складі
    location = models.CharField(
        'Місце зберігання',
        max_length=100,
        blank=True,
        help_text='Полиця, секція, тощо'
    )
    
    updated_at = models.DateTimeField('Оновлено', auto_now=True)

    class Meta:
        verbose_name = 'Залишок на складі'
        verbose_name_plural = 'Залишки на складі'
        unique_together = ['warehouse', 'product']

    def __str__(self):
        return f"{self.product} @ {self.warehouse}: {self.quantity}"

    @property
    def available(self):
        """Доступна кількість (без резерву)"""
        return self.quantity - self.reserved

    @property
    def is_low_stock(self):
        """Чи низький залишок"""
        return self.quantity <= self.product.min_stock_level


class StockMovement(models.Model):
    """
    Рух товару по складу
    """
    MOVEMENT_TYPES = [
        ('in', 'Надходження'),
        ('out', 'Витрата'),
        ('transfer', 'Переміщення'),
        ('adjustment', 'Інвентаризація'),
        ('return', 'Повернення'),
        ('write_off', 'Списання'),
    ]

    movement_type = models.CharField(
        'Тип руху',
        max_length=20,
        choices=MOVEMENT_TYPES
    )
    
    product = models.ForeignKey(
        Part,
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name='Товар'
    )
    quantity = models.DecimalField(
        'Кількість',
        max_digits=12, decimal_places=2
    )
    
    # Склади
    warehouse_from = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='movements_out',
        verbose_name='Зі складу',
        null=True, blank=True
    )
    warehouse_to = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='movements_in',
        verbose_name='На склад',
        null=True, blank=True
    )
    
    service_order = models.ForeignKey(
        'orders.ServiceOrder',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='stock_movements',
        verbose_name='Наряд-замовлення'
    )
    
    # Інформація про надходження
    supplier = models.CharField('Постачальник', max_length=200, blank=True)
    invoice_number = models.CharField('Номер накладної', max_length=50, blank=True)
    purchase_price = models.DecimalField(
        'Закупівельна ціна',
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    
    notes = models.TextField('Примітки', blank=True)
    
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_movements',
        verbose_name='Створив'
    )
    created_at = models.DateTimeField('Створено', auto_now_add=True)

    class Meta:
        verbose_name = 'Рух товару'
        verbose_name_plural = 'Рух товарів'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()}: {self.product} ({self.quantity})"

    def save(self, *args, **kwargs):
        """Автоматичне оновлення залишків при збереженні"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            self._update_stock()

    def _update_stock(self):
        """Оновлення залишків на складах"""
        if self.movement_type == 'in' and self.warehouse_to:
            # Надходження
            stock, _ = Stock.objects.get_or_create(
                warehouse=self.warehouse_to,
                product=self.product
            )
            stock.quantity += self.quantity
            stock.save()
            
        elif self.movement_type == 'out' and self.warehouse_from:
            # Витрата
            stock = Stock.objects.get(
                warehouse=self.warehouse_from,
                product=self.product
            )
            stock.quantity -= self.quantity
            stock.save()
            
        elif self.movement_type == 'transfer':
            # Переміщення
            if self.warehouse_from:
                stock_from = Stock.objects.get(
                    warehouse=self.warehouse_from,
                    product=self.product
                )
                stock_from.quantity -= self.quantity
                stock_from.save()
            
            if self.warehouse_to:
                stock_to, _ = Stock.objects.get_or_create(
                    warehouse=self.warehouse_to,
                    product=self.product
                )
                stock_to.quantity += self.quantity
                stock_to.save()


class UsedPart(models.Model):
    """Існуюча модель - залишаємо для сумісності"""
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
    
    # Нове поле - з якого складу
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        null=True, blank=True,
        verbose_name='Склад'
    )

    class Meta:
        verbose_name = "Використана запчастина"
        verbose_name_plural = "Використані запчастини"
        unique_together = ('service_work', 'part')

    def __str__(self):
        return f"{self.part.name} - {self.quantity} шт."