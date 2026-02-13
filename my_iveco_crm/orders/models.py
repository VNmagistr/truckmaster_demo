from django.db import models
from django.conf import settings
from django.db.models import Sum, F
from django.utils import timezone

# Імпортуємо тільки існуючі моделі
from clients.models import Client, Truck, IvecoBaseModel
from inventory.models import UsedPart, Warehouse, StockItem, Product


def get_repair_photo_path(instance, filename):
    return f'repair_photos/{instance.service_order.id}/{filename}'


class ServiceOrderManager(models.Manager):
    def active(self):
        return self.filter(status__in=['OPEN', 'IN_PROGRESS'])
    
    def for_client(self, client):
        return self.filter(client=client).select_related('truck', 'client')
    
    def for_truck(self, truck):
        return self.filter(truck=truck).select_related('client')


class WorkGroup(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва категорії робіт")
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    
    class Meta:
        verbose_name = "Група робіт"
        verbose_name_plural = "Групи робіт"
    
    def __str__(self): 
        return self.name


class WorkPrice(models.Model):
    work_group = models.ForeignKey(WorkGroup, on_delete=models.CASCADE, related_name='works')
    name = models.CharField(max_length=255, verbose_name="Назва роботи")
    standard_hours = models.DecimalField(max_digits=5, decimal_places=2, default=1)

    class Meta:
        verbose_name = "Робота"
        verbose_name_plural = "Роботи"

    def __str__(self): 
        return self.name
    
    @property
    def price(self):
        return self.standard_hours * self.work_group.hourly_rate
    
    def get_calculated_price(self):
        return self.price


class ServiceOrder(models.Model):
    class StatusChoices(models.TextChoices):
        OPEN = 'OPEN', 'Відкрито'
        IN_PROGRESS = 'IN_PROGRESS', 'В роботі'
        DONE = 'DONE', 'Виконано'
        CLOSED = 'CLOSED', 'Закрито'
        CANCELED = 'CANCELED', 'Скасовано'

    order_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, verbose_name="Клієнт")
    truck = models.ForeignKey(Truck, on_delete=models.PROTECT, verbose_name="Вантажівка")
    current_mileage = models.PositiveIntegerField(null=True, blank=True, verbose_name="Поточний пробіг")
    problem_description = models.TextField(blank=True, verbose_name="Опис проблеми")
    recommendations = models.TextField(blank=True, verbose_name="Рекомендації")
    car_photo = models.ImageField(upload_to='order_photos/cars/', blank=True, null=True)
    odometer_photo = models.ImageField(upload_to='order_photos/odometers/', blank=True, null=True)
    dashboard_photo = models.ImageField(upload_to='order_photos/dashboards/', blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.OPEN, verbose_name="Статус")
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Загальна вартість")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Створено")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Оновлено")

    marked_for_deletion = models.BooleanField(default=False, verbose_name="Позначено на видалення")
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
        verbose_name = "Наряд-замовлення"
        verbose_name_plural = "Наряди-замовлення"
        ordering = ['-created_at']

    def __str__(self): 
        return f"№{self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"SO-{timezone.now().strftime('%Y%m%d')}-{ServiceOrder.objects.count()+1:04d}"
        super().save(*args, **kwargs)

    def update_total_cost(self):
        works_cost = sum(w.amount for w in self.works.all())
        parts_cost = UsedPart.objects.filter(
            service_work__service_order=self
        ).aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or 0
        self.total_cost = works_cost + parts_cost
        self.save(update_fields=['total_cost'])


class ServiceWork(models.Model):
    service_order = models.ForeignKey(
        ServiceOrder, 
        on_delete=models.CASCADE, 
        related_name="works",
        verbose_name="Наряд-замовлення"
    )
    work = models.ForeignKey(
        WorkPrice, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="Робота"
    )
    description = models.TextField(blank=True, verbose_name="Опис")
    mechanic = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Механік"
    )
    hours_spent = models.DecimalField(max_digits=5, decimal_places=2, default=1, verbose_name="Витрачено годин")
    price_at_moment = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ціна")

    class Meta:
        verbose_name = "Виконана робота"
        verbose_name_plural = "Виконані роботи"

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

    class Meta:
        verbose_name = "Фото ремонту"
        verbose_name_plural = "Фото ремонтів"


class MaintenanceRule(models.Model):
    name = models.CharField(max_length=255, verbose_name="Назва")
    km_interval = models.PositiveIntegerField(verbose_name="Інтервал (км)")
    applicable_models = models.ManyToManyField(IvecoBaseModel, verbose_name="Застосовні моделі")
    
    class Meta:
        verbose_name = "Правило ТО"
        verbose_name_plural = "Правила ТО"
    
    def __str__(self): 
        return self.name


class MaintenanceLog(models.Model):
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, verbose_name="Вантажівка")
    rule = models.ForeignKey(MaintenanceRule, on_delete=models.CASCADE, verbose_name="Правило")
    date_performed = models.DateField(verbose_name="Дата виконання")
    mileage = models.PositiveIntegerField(null=True, blank=True, verbose_name="Пробіг")

    class Meta:
        verbose_name = "Запис ТО"
        verbose_name_plural = "Записи ТО"


class FilterType(models.Model):
    EURO_CHOICES = [
        ('EURO3', 'Євро-3'),
        ('EURO4', 'Євро-4'),
        ('EURO5', 'Євро-5'),
        ('EURO6', 'Євро-6'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Назва")
    euro_standard = models.CharField(
        max_length=10, 
        choices=EURO_CHOICES, 
        blank=True,
        verbose_name="Євростандарт"
    )
    replacement_interval_km = models.PositiveIntegerField(default=20000, verbose_name="Інтервал заміни (км)")
    applicable_models = models.ManyToManyField(IvecoBaseModel, blank=True, verbose_name="Застосовні моделі")
    
    class Meta:
        verbose_name = "Тип фільтра"
        verbose_name_plural = "Типи фільтрів"
    
    def __str__(self): 
        return self.name


class MaintenanceKit(models.Model):
    truck = models.OneToOneField(
        Truck, 
        on_delete=models.CASCADE,
        verbose_name="Вантажівка"
    )
    # Використовуємо Product замість Part
    oil = models.ForeignKey(
        'inventory.Product', 
        on_delete=models.PROTECT, 
        related_name='oil_for_trucks',
        verbose_name="Олива"
    )
    oil_quantity = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Кількість оливи")

    class Meta:
        verbose_name = "Комплект ТО"
        verbose_name_plural = "Комплекти ТО"


class MaintenanceKitFilter(models.Model):
    maintenance_kit = models.ForeignKey(
        MaintenanceKit, 
        on_delete=models.CASCADE, 
        related_name='filters',
        verbose_name="Комплект ТО"
    )
    filter_type = models.ForeignKey(
        FilterType, 
        on_delete=models.PROTECT,
        verbose_name="Тип фільтра"
    )
    # Використовуємо Product замість Part
    part = models.ForeignKey(
        'inventory.Product', 
        on_delete=models.PROTECT,
        verbose_name="Запчастина"
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="Кількість")

    class Meta:
        verbose_name = "Фільтр комплекту ТО"
        verbose_name_plural = "Фільтри комплектів ТО"