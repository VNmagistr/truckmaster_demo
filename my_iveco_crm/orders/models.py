from django.db import models
from django.conf import settings
from django.db.models import Sum, F, Max
from decimal import Decimal
from django.utils import timezone

# Імпорти з інших додатків
from clients.models import Client, Truck, IvecoBaseModel
from inventory.models import UsedPart, Warehouse, Stock, Part

# Функція для шляхів фото
def get_repair_photo_path(instance, filename):
    return f'repair_photos/{instance.service_order.id}/{filename}'

# --- МЕНЕДЖЕРИ ---

class ServiceOrderManager(models.Manager):
    def active(self):
        """Тільки активні замовлення"""
        return self.filter(status__in=['OPEN', 'IN_PROGRESS'])
    
    def for_client(self, client):
        return self.filter(client=client).select_related('truck', 'client')
    
    def for_truck(self, truck):
        return self.filter(truck=truck).select_related('client')

# --- КАТЕГОРІЇ ТА ПРАЙС ---

class WorkGroup(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва категорії робіт")
    hourly_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=500,
        verbose_name="Вартість нормо-години (грн)"
    )
    
    class Meta:
        verbose_name = "Категорія робіт"
        verbose_name_plural = "Категорії робіт"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.hourly_rate} грн/год)"

class WorkPrice(models.Model):
    """Каталог типових робіт (Прайс-лист)"""
    work_group = models.ForeignKey(WorkGroup, on_delete=models.CASCADE, verbose_name="Категорія робіт")
    name = models.CharField(max_length=255, verbose_name="Назва роботи")
    standard_hours = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=1,
        verbose_name="Нормо-годин"
    )

    class Meta:
        verbose_name = "Робота з прайсу"
        verbose_name_plural = "Роботи з прайсу"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.standard_hours} н/г)"
    
    @property
    def price(self):
        return self.standard_hours * self.work_group.hourly_rate
    
    def get_calculated_price(self):
        return self.price

# --- ГОЛОВНА МОДЕЛЬ ЗАМОВЛЕННЯ ---

class ServiceOrder(models.Model):
    class StatusChoices(models.TextChoices):
        OPEN = 'OPEN', 'Відкрито'
        IN_PROGRESS = 'IN_PROGRESS', 'В роботі'
        DONE = 'DONE', 'Виконано (Очікує оплати)'
        CLOSED = 'CLOSED', 'Закрито (Оплачено)'
        CANCELED = 'CANCELED', 'Скасовано'

    order_number = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Номер наряду")
    
    # Клієнт та Авто
    client = models.ForeignKey(Client, on_delete=models.PROTECT, verbose_name="Клієнт")
    truck = models.ForeignKey(Truck, on_delete=models.PROTECT, verbose_name="Вантажівка")
    
    # Прийомка (Фото + Пробіг)
    current_mileage = models.PositiveIntegerField(verbose_name="Пробіг при заїзді (км)", null=True, blank=True)
    problem_description = models.TextField(blank=True, verbose_name="Скарги клієнта")
    
    car_photo = models.ImageField(upload_to='order_photos/cars/', verbose_name='Фото авто/номера', blank=True, null=True)
    odometer_photo = models.ImageField(upload_to='order_photos/odometers/', verbose_name='Фото одометра', blank=True, null=True)
    dashboard_photo = models.ImageField(upload_to='order_photos/dashboards/', verbose_name='Фото панелі приладів', blank=True, null=True)
    
    # Статуси та фінанси
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.OPEN, verbose_name="Статус")
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Загальна вартість")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Створено")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Оновлено")

    # М'яке видалення
    marked_for_deletion = models.BooleanField(default=False, verbose_name="Видалити?")
    deletion_reason = models.TextField(blank=True, verbose_name="Причина видалення")
    marked_for_deletion_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders_marked_for_deletion',
        verbose_name="Позначив на видалення"
    )
    marked_for_deletion_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата позначення")

    objects = ServiceOrderManager()

    class Meta:
        verbose_name = "Замовлення-наряд"
        verbose_name_plural = "Замовлення-наряди"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"№{self.order_number} | {self.truck.license_plate}"

    def save(self, *args, **kwargs):
        # 1. Генерація номера (SO-YYYYMMDD-XXXX)
        if not self.order_number:
            today = timezone.now()
            prefix = f"SO-{today.strftime('%Y%m%d')}"
            last_order = ServiceOrder.objects.filter(order_number__startswith=prefix).order_by('-order_number').first()
            if last_order and last_order.order_number:
                last_num = int(last_order.order_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.order_number = f"{prefix}-{new_num:04d}"
        
        # 2. Оновлення пробігу вантажівки (якщо вказано новий і він більший)
        if self.pk is None and self.truck and self.current_mileage:
             if self.current_mileage > self.truck.current_odometer:
                 self.truck.current_odometer = self.current_mileage
                 self.truck.save(update_fields=['current_odometer'])

        super().save(*args, **kwargs)

    def update_total_cost(self):
        """Перерахунок суми: Роботи + Запчастини"""
        # Вартість робіт
        works_cost = sum(w.amount for w in self.works.all())
        
        # Вартість запчастин (прив'язаних до робіт)
        parts_cost = UsedPart.objects.filter(service_work__service_order=self).aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or Decimal('0')
        
        # Вартість запчастин (прямих)
        direct_parts_cost = self.direct_parts.aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or Decimal('0')

        self.total_cost = works_cost + parts_cost + direct_parts_cost
        self.save(update_fields=['total_cost'])

# --- ВИКОНАНІ РОБОТИ (З прив'язкою до механіка) ---

class ServiceWork(models.Model):
    service_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name="works", verbose_name="Наряд")
    work = models.ForeignKey(WorkPrice, on_delete=models.SET_NULL, null=True, verbose_name="Робота з прайсу")
    description = models.TextField(verbose_name="Додатковий опис", blank=True)
    
    # ВАЖЛИВО: Прив'язка до реального користувача (система ролей)
    mechanic = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Механік"
    )
    
    hours_spent = models.DecimalField(max_digits=5, decimal_places=2, default=1, verbose_name="Витрачено годин")
    price_at_moment = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ціна (фіксована)")

    class Meta:
        verbose_name = "Робота в наряді"
        verbose_name_plural = "Роботи в наряді"

    @property
    def amount(self):
        return self.price_at_moment * self.hours_spent

    def save(self, *args, **kwargs):
        if not self.price_at_moment and self.work:
            self.price_at_moment = self.work.get_calculated_price()
        super().save(*args, **kwargs)
        self.service_order.update_total_cost()


class RepairPhoto(models.Model):
    service_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='repair_photos/')
    description = models.CharField(max_length=255, blank=True)

# --- МОДЕЛІ РЕГЛАМЕНТІВ І КОМПЛЕКТАЦІЇ (Відновлені) ---

class MaintenanceRule(models.Model):
    name = models.CharField(max_length=255, verbose_name="Назва правила")
    description = models.TextField(verbose_name="Опис", blank=True)
    applicable_models = models.ManyToManyField(IvecoBaseModel, verbose_name="Застосовується до моделей")
    
    km_interval = models.PositiveIntegerField(
        verbose_name="Інтервал (км)",
        help_text="Через яку кількість кілометрів потрібно виконувати це правило"
    )

    class Meta:
        verbose_name = "Правило регламенту"
        verbose_name_plural = "Правила регламентів"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (кожні {self.km_interval} км)"

class MaintenanceLog(models.Model):
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, verbose_name="Вантажівка")
    rule = models.ForeignKey(MaintenanceRule, on_delete=models.CASCADE, verbose_name="Правило регламенту")
    date_performed = models.DateField(verbose_name="Дата виконання")
    notes = models.TextField(blank=True, verbose_name="Примітки")

    class Meta:
        verbose_name = "Журнал регламентних робіт"
        verbose_name_plural = "Журнал регламентних робіт"
        ordering = ['-date_performed']

class FilterType(models.Model):
    EURO_STANDARD_CHOICES = [
        ('EURO3', 'Євро-3'),
        ('EURO4', 'Євро-4'),
        ('EURO5', 'Євро-5'),
        ('EURO6', 'Євро-6'),
    ]
    name = models.CharField(max_length=100, verbose_name="Назва типу фільтра")
    description = models.TextField(blank=True, verbose_name="Опис")
    applicable_models = models.ManyToManyField(IvecoBaseModel, blank=True, verbose_name="Застосовується до моделей")
    euro_standard = models.CharField(max_length=10, choices=EURO_STANDARD_CHOICES, blank=True, null=True, verbose_name="Євростандарт")
    replacement_interval_km = models.PositiveIntegerField(default=20000, verbose_name="Інтервал заміни (км)")
    
    class Meta:
        verbose_name = "Тип фільтра"
        verbose_name_plural = "Типи фільтрів"
        ordering = ['name']
    
    def __str__(self):
        res = self.name
        if self.euro_standard: res += f" ({self.get_euro_standard_display()})"
        return res

class MaintenanceKit(models.Model):
    truck = models.OneToOneField(Truck, on_delete=models.CASCADE, related_name='maintenance_kit', verbose_name="Вантажівка (по VIN)")
    oil = models.ForeignKey(Part, on_delete=models.PROTECT, related_name='oil_for_trucks', verbose_name="Моторна олива")
    oil_quantity = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Кількість оливи (л)")
    oil_replacement_interval = models.PositiveIntegerField(default=30000, verbose_name="Інтервал заміни оливи (км)")
    notes = models.TextField(blank=True, verbose_name="Примітки")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Набір для ТО"
        verbose_name_plural = "Набори для ТО"
    
    def __str__(self):
        return f"Набір ТО для VIN: {self.truck.last_seven_vin}"
    
    def check_availability(self, warehouse=None):
        if warehouse: warehouses = [warehouse]
        else: warehouses = Warehouse.objects.filter(is_active=True)
        missing = []
        oil_available = Stock.objects.filter(product=self.oil, warehouse__in=warehouses).aggregate(total=Sum('quantity'))['total'] or 0
        if oil_available < self.oil_quantity: missing.append(f"{self.oil.name}: потрібно {self.oil_quantity}л, є {oil_available}л")
        for kit_filter in self.filters.all():
            available = Stock.objects.filter(product=kit_filter.part, warehouse__in=warehouses).aggregate(total=Sum('quantity'))['total'] or 0
            if available < kit_filter.quantity: missing.append(f"{kit_filter.part.name}: потрібно {kit_filter.quantity}шт, є {available}шт")
        return {'available': len(missing) == 0, 'missing': missing}

class MaintenanceKitFilter(models.Model):
    maintenance_kit = models.ForeignKey(MaintenanceKit, on_delete=models.CASCADE, related_name='filters', verbose_name="Набір ТО")
    filter_type = models.ForeignKey(FilterType, on_delete=models.PROTECT, verbose_name="Тип фільтра")
    part = models.ForeignKey(Part, on_delete=models.PROTECT, verbose_name="Запчастина (фільтр)")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Кількість")
    custom_interval_km = models.PositiveIntegerField(null=True, blank=True, verbose_name="Індивідуальний інтервал (км)")
    notes = models.CharField(max_length=255, blank=True, verbose_name="Примітка")
    
    class Meta:
        verbose_name = "Фільтр у наборі"
        verbose_name_plural = "Фільтри у наборі"
        ordering = ['filter_type__name']
    
    def __str__(self):
        return f"{self.filter_type.name}: {self.part.name}"