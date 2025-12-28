from django.db import models
from clients.models import Client, Truck, IvecoBaseModel
from inventory.models import UsedPart
from django.db.models import Sum, F
from decimal import Decimal

# Ця функція потрібна для старих файлів міграцій
def get_repair_photo_path(instance, filename):
    return f'repair_photos/{instance.service_order.id}/{filename}'

# --- Моделі ---

class ServiceOrderManager(models.Manager):
    def active(self):
        """Тільки активні замовлення"""
        return self.filter(status__in=['OPEN', 'IN_PROGRESS'])
    
    def for_client(self, client):
        """Замовлення клієнта"""
        return self.filter(client=client).select_related('truck', 'client')
    
    def for_truck(self, truck):
        """Замовлення для вантажівки"""
        return self.filter(truck=truck).select_related('client')

class Employee(models.Model):
    name = models.CharField(max_length=100, verbose_name="Ім'я")
    position = models.CharField(max_length=100, verbose_name="Посада")
    
    class Meta:
        verbose_name = "Працівник"
        verbose_name_plural = "Працівники"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.position})"

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

class ServiceOrder(models.Model):
    class StatusChoices(models.TextChoices):
        OPEN = 'OPEN', 'Відкрито'
        IN_PROGRESS = 'IN_PROGRESS', 'В роботі'
        CLOSED = 'CLOSED', 'Закрито'
        CANCELED = 'CANCELED', 'Скасовано'

    order_number = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Номер замовлення-наряду")
    client = models.ForeignKey(Client, on_delete=models.PROTECT, verbose_name="Клієнт", blank=True, null=True)
    truck = models.ForeignKey(Truck, on_delete=models.PROTECT, verbose_name="Вантажівка", blank=True, null=True)
    
    problem_description = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Опис проблеми (зі слів клієнта)"
    )
    
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.OPEN,
        verbose_name="Статус"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата оновлення")
    total_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="Загальна вартість"
    )

    class Meta:
        verbose_name = "Замовлення-наряд"
        verbose_name_plural = "Замовлення-наряди"
        ordering = ['-created_at']
    
    def __str__(self):
        client_name = self.client.name if self.client else 'Н/Д'
        order_num = self.order_number if self.order_number else 'Без номера'
        return f"Замовлення №{order_num} ({client_name})"

    def update_total_cost(self):
        """Оптимізований підрахунок вартості: роботи + всі запчастини"""
        
        # 1. Вартість робіт
        works = self.works.select_related('work__work_group').filter(work__isnull=False)
        total_work_cost = sum(
            work.work.get_calculated_price() * (work.hours_spent or Decimal('1'))
            for work in works
        )
        
        # 2. Вартість запчастин через роботи
        parts_via_works = UsedPart.objects.filter(
            service_work__service_order=self
        ).aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or Decimal('0')
        
        # 3. Вартість запчастин доданих напряму до замовлення
        direct_parts = self.direct_parts.aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or Decimal('0')
        
        # Підсумок
        new_total = total_work_cost + parts_via_works + direct_parts
        
        # Оновлюємо тільки якщо змінилося
        if self.total_cost != new_total:
            self.total_cost = new_total
            self.save(update_fields=['total_cost'])
        
        return self.total_cost

class ServiceWork(models.Model):
    service_order = models.ForeignKey('ServiceOrder', on_delete=models.CASCADE, related_name="works", verbose_name="Замовлення-наряд")
    
    work = models.ForeignKey(
        'WorkPrice', 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Виконана робота (з прайсу)"
    )
    
    description = models.TextField(
        verbose_name="Опис виконаних робіт (додатково)",
        blank=True,
        null=True
    )
    
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, verbose_name="Виконавець")
    hours_spent = models.DecimalField(max_digits=5, decimal_places=2, default=1, verbose_name="Витрачено годин")
    
    class Meta:
        verbose_name = "Виконана робота"
        verbose_name_plural = "Виконані роботи"
        ordering = ['-service_order']
    
    def __str__(self):
        if self.work:
            return f"{self.work.name} (Замовлення №{self.service_order.order_number})"
        return f"Робота без назви (Замовлення №{self.service_order.order_number})"

class RepairPhoto(models.Model):
    service_order = models.ForeignKey('ServiceOrder', on_delete=models.CASCADE, related_name='photos', verbose_name="Замовлення-наряд")
    image = models.ImageField(upload_to='repair_photos/', verbose_name="Зображення")
    description = models.CharField(max_length=255, blank=True, verbose_name="Опис")
    
    class Meta:
        verbose_name = "Фото ремонту"
        verbose_name_plural = "Фото ремонту"
        ordering = ['-service_order']

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

class WorkPrice(models.Model):
    """Робота з прайсу з автоматичним розрахунком ціни"""
    
    work_group = models.ForeignKey(
        WorkGroup, 
        on_delete=models.CASCADE, 
        verbose_name="Категорія робіт"
    )
    name = models.CharField(max_length=255, verbose_name="Назва роботи")
    standard_hours = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=1,
        verbose_name="Нормо-годин (стандартна тривалість)"
    )

    class Meta:
        verbose_name = "Робота з прайсу"
        verbose_name_plural = "Роботи з прайсу"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.standard_hours} н/г)"
    
    @property
    def price(self):
        """Розраховує ціну: нормо-години × вартість години категорії"""
        return self.standard_hours * self.work_group.hourly_rate
    
    def get_calculated_price(self):
        """Метод для явного розрахунку ціни (для backward compatibility)"""
        return self.price
    
class FilterType(models.Model):
    """Типи фільтрів (масляний, паливний, AdBlue тощо)"""
    
    EURO_STANDARD_CHOICES = [
        ('EURO3', 'Євро-3'),
        ('EURO4', 'Євро-4'),
        ('EURO5', 'Євро-5'),
        ('EURO6', 'Євро-6'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Назва типу фільтра")
    description = models.TextField(blank=True, verbose_name="Опис")
    
    # Прив'язка до моделі та євростандарту
    applicable_models = models.ManyToManyField(
        'clients.IvecoBaseModel',
        blank=True,
        verbose_name="Застосовується до моделей",
        help_text="Залиште порожнім якщо підходить для всіх моделей"
    )
    euro_standard = models.CharField(
        max_length=10,
        choices=EURO_STANDARD_CHOICES,
        blank=True,
        null=True,
        verbose_name="Євростандарт",
        help_text="Залиште порожнім якщо підходить для всіх стандартів"
    )
    
    replacement_interval_km = models.PositiveIntegerField(
        default=20000,
        verbose_name="Інтервал заміни (км)",
        help_text="Стандартний інтервал заміни для цього типу"
    )
    
    class Meta:
        verbose_name = "Тип фільтра"
        verbose_name_plural = "Типи фільтрів"
        ordering = ['name']
        # Унікальність: ім'я + модель + євростандарт
        # (можна мати "Паливний фільтр" для Євро-4 і окремий для Євро-6)
    
    def __str__(self):
        result = self.name
        if self.euro_standard:
            result += f" ({self.get_euro_standard_display()})"
        return result


class MaintenanceKit(models.Model):
    """Набір оливи та фільтрів для конкретного автомобіля (прив'язка по VIN)"""
    truck = models.OneToOneField(
        'clients.Truck', 
        on_delete=models.CASCADE, 
        related_name='maintenance_kit',
        verbose_name="Вантажівка (по VIN)"
    )
    
    # Олива
    oil = models.ForeignKey(
        'inventory.Part', 
        on_delete=models.PROTECT, 
        related_name='oil_for_trucks',
        verbose_name="Моторна олива"
    )
    oil_quantity = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        verbose_name="Кількість оливи (л)"
    )
    oil_replacement_interval = models.PositiveIntegerField(
        default=30000,
        verbose_name="Інтервал заміни оливи (км)"
    )
    
    notes = models.TextField(blank=True, verbose_name="Примітки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Створено")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Оновлено")
    
    class Meta:
        verbose_name = "Набір для ТО"
        verbose_name_plural = "Набори для ТО"
    
    def __str__(self):
        return f"Набір ТО для VIN: {self.truck.last_seven_vin} ({self.truck.license_plate})"
    
    def get_total_cost(self):
        """Розрахунок вартості комплекту ТО"""
        oil_cost = self.oil.selling_price * self.oil_quantity
        filters_cost = sum(
            f.part.selling_price * f.quantity 
            for f in self.filters.all()
        )
        return oil_cost + filters_cost
    
    def check_availability(self, warehouse=None):
        """Перевірка наявності всіх компонентів"""
        if warehouse:
            warehouses = [warehouse]
        else:
            warehouses = Warehouse.objects.filter(is_active=True)
        
        missing = []
        
        # Перевірка оливи
        oil_available = Stock.objects.filter(
            product=self.oil,
            warehouse__in=warehouses
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        if oil_available < self.oil_quantity:
            missing.append(f"{self.oil.name}: потрібно {self.oil_quantity}л, є {oil_available}л")
        
        # Перевірка фільтрів
        for kit_filter in self.filters.all():
            available = Stock.objects.filter(
                product=kit_filter.part,
                warehouse__in=warehouses
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            if available < kit_filter.quantity:
                missing.append(
                    f"{kit_filter.part.name}: потрібно {kit_filter.quantity}шт, "
                    f"є {available}шт"
                )
        
        return {
            'available': len(missing) == 0,
            'missing': missing
        }


class MaintenanceKitFilter(models.Model):
    """Фільтр у наборі ТО (може бути декілька однакових типів)"""
    maintenance_kit = models.ForeignKey(
        MaintenanceKit,
        on_delete=models.CASCADE,
        related_name='filters',
        verbose_name="Набір ТО"
    )
    filter_type = models.ForeignKey(
        FilterType,
        on_delete=models.PROTECT,
        verbose_name="Тип фільтра"
    )
    part = models.ForeignKey(
        'inventory.Part',
        on_delete=models.PROTECT,
        verbose_name="Запчастина (фільтр)"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Кількість",
        help_text="Скільки таких фільтрів потрібно"
    )
    custom_interval_km = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Індивідуальний інтервал (км)",
        help_text="Залиште порожнім для використання стандартного інтервалу типу"
    )
    notes = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Примітка",
        help_text="Наприклад: 'грубої очистки', 'тонкої очистки'"
    )
    
    class Meta:
        verbose_name = "Фільтр у наборі"
        verbose_name_plural = "Фільтри у наборі"
        ordering = ['filter_type__name']
    
    def __str__(self):
        note = f" ({self.notes})" if self.notes else ""
        return f"{self.filter_type.name}{note}: {self.part.name} × {self.quantity}"
    
    @property
    def replacement_interval(self):
        """Повертає інтервал заміни (індивідуальний або стандартний)"""
        return self.custom_interval_km or self.filter_type.replacement_interval_km