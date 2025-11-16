from django.db import models
from clients.models import Client, Truck, IvecoBaseModel
from inventory.models import Part
from django.db.models import Sum, F

# Ця функція потрібна для старих файлів міграцій
def get_repair_photo_path(instance, filename):
    return f'repair_photos/{instance.service_order.id}/{filename}'

# --- Моделі ---

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
    
    class Meta:
        verbose_name = "Категорія робіт"
        verbose_name_plural = "Категорії робіт"
        ordering = ['name']
    
    def __str__(self):
        return self.name

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
    
    # 👇 ДОДАНО НОВЕ ПОЛЕ ДЛЯ ЗАГАЛЬНОЇ ВАРТОСТІ 👇
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

    # 👇 ДОДАНО МЕТОД, ЯКИЙ ВИКЛИКАЄ ПОМИЛКУ 👇
    def update_total_cost(self):
        """
        Перераховує загальну вартість замовлення на основі всіх пов'язаних робіт.
        """
        # Обчислюємо вартість: ціна_роботи * витрачені_години
        total_work_cost = self.works.filter(work__isnull=False).aggregate(
        total=Sum(F('work__price') * F('hours_spent'))
        )['total'] or 0
        
        # NOTE: Тут ви також можете додати логіку для розрахунку вартості запчастин,
        # якщо ServiceWork має посилання на UsedPart
        
        self.total_cost = total_work_cost
        self.save(update_fields=['total_cost']) # Зберігаємо лише змінене поле


class ServiceWork(models.Model):
    service_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name="works", verbose_name="Замовлення-наряд")
    
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

# ... (Решта моделей без змін) ...
class RepairPhoto(models.Model):
    service_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='photos', verbose_name="Замовлення-наряд")
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
    work_group = models.ForeignKey(WorkGroup, on_delete=models.CASCADE, verbose_name="Категорія робіт")
    name = models.CharField(max_length=255, verbose_name="Назва роботи")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна")

    class Meta:
        verbose_name = "Робота з прайсу"
        verbose_name_plural = "Роботи з прайсу"
        ordering = ['name']

    def __str__(self):
        return self.name