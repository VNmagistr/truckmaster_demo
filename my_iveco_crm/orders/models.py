from django.db import models
from django.conf import settings
from django.db.models import Sum, F
from decimal import Decimal
from django.utils import timezone

# Імпорти з інших додатків
from clients.models import Client, Truck, IvecoBaseModel
from inventory.models import UsedPart, Warehouse, Stock

# Функція для шляхів фото
def get_repair_photo_path(instance, filename):
    return f'repair_photos/{instance.service_order.id}/{filename}'

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
    current_mileage = models.PositiveIntegerField(verbose_name="Пробіг при заїзді (км)")
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
            new_num = int(last_order.order_number.split('-')[-1]) + 1 if last_order else 1
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
        settings.AUTH_USER_MODEL, # Це зв'яже з твоєю моделлю User/UserProfile
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
        # Якщо ціна не зафіксована, беремо з прайсу
        if not self.price_at_moment and self.work:
            self.price_at_moment = self.work.get_calculated_price()
        super().save(*args, **kwargs)
        # Оновлюємо загальну суму замовлення
        self.service_order.update_total_cost()


class RepairPhoto(models.Model):
    service_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='repair_photos/')
    description = models.CharField(max_length=255, blank=True)
    