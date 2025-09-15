# orders/models.py

from django.db import models
from django.db.models import Sum, F
from clients.models import Client, Truck, IvecoBaseModel
from inventory.models import UsedPart

class Employee(models.Model):
    """
    Працівник СТО (майстер, менеджер).
    """
    name = models.CharField(max_length=255, verbose_name="Ім'я та прізвище")
    position = models.CharField(max_length=100, verbose_name="Посада")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Номер телефону")

    class Meta:
        verbose_name = "Працівник"
        verbose_name_plural = "Працівники"

    def __str__(self):
        return self.name

class ServiceOrder(models.Model):
    """
    Замовлення-наряд, основний документ по роботі з автомобілем.
    """
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, verbose_name="Автомобіль")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Клієнт")
    
    class StatusChoices(models.TextChoices):
        NEW = 'new', 'Нове'
        IN_PROGRESS = 'in_progress', 'В роботі'
        COMPLETED = 'completed', 'Завершено'
        CANCELED = 'canceled', 'Скасовано'

    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.NEW, verbose_name="Статус")
    description = models.TextField(verbose_name="Причина звернення / Скарги клієнта")
    start_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата відкриття")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата закриття")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Загальна вартість")

    def update_total_cost(self):
        """
        Обчислює загальну вартість на основі робіт та запчастин.
        """
        # Рахуємо суму вартості всіх робіт
        works_cost = self.works.aggregate(total=Sum('labor_cost'))['total'] or 0

        # Рахуємо суму вартості всіх запчастин 
        # (кількість * ціна)
        parts_cost = UsedPart.objects.filter(service_work__service_order=self).aggregate(
            total=Sum(F('quantity') * F('part__price'), output_field=models.DecimalField())
        )['total'] or 0

        self.total_cost = works_cost + parts_cost
        self.save(update_fields=['total_cost']) # Зберігаємо тільки це поле

    class Meta:
        verbose_name = "Замовлення-наряд"
        verbose_name_plural = "Замовлення-наряди"
        ordering = ['-start_date']

    def __str__(self):
        return f"Замовлення №{self.id} для {self.truck.license_plate}"

class ServiceWork(models.Model):
    """
    Конкретна робота, виконана в рамках замовлення-наряду.
    """
    service_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name="works", verbose_name="Замовлення-наряд")
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Виконавець")
    job_description = models.CharField(max_length=255, verbose_name="Опис роботи")
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Вартість роботи")
    duration_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Витрачено годин")

    class Meta:
        verbose_name = "Виконана робота"
        verbose_name_plural = "Виконані роботи"

    def __str__(self):
        return self.job_description

class MaintenanceRule(models.Model):
    """
    Правило для відстеження регламентних робіт.
    """
    name = models.CharField(max_length=255, verbose_name="Назва регламентної роботи")
    interval_km = models.PositiveIntegerField(verbose_name="Інтервал пробігу (км)")
    applicable_models = models.ManyToManyField(IvecoBaseModel, verbose_name="Застосовується до базових моделей")

    class TransmissionChoices(models.TextChoices):
        ANY = 'any', 'Будь-яка'
        MANUAL = 'manual', 'Механічна'
        AUTOMATIC = 'automatic', 'Автоматична'
        ROBOT = 'robot', 'Робот'

    applicable_transmission = models.CharField(
        max_length=10,
        choices=TransmissionChoices.choices,
        default=TransmissionChoices.ANY,
        verbose_name="Застосовується до типу КПП"
    )

    class Meta:
        verbose_name = "Правило регламенту"
        verbose_name_plural = "Правила регламентів"

    def __str__(self):
        return f"{self.name} (кожні {self.interval_km} км)"

class MaintenanceLog(models.Model):
    """
    Журнал фіксації виконаних регламентних робіт для конкретної вантажівки.
    """
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, verbose_name="Вантажівка")
    rule = models.ForeignKey(MaintenanceRule, on_delete=models.CASCADE, verbose_name="Виконане правило")
    completion_date = models.DateField(auto_now_add=True, verbose_name="Дата виконання")
    completion_mileage = models.PositiveIntegerField(verbose_name="Пробіг на момент виконання (км)")

    class Meta:
        verbose_name = "Запис у журналі регламенту"
        verbose_name_plural = "Журнал регламентних робіт"
        ordering = ['-completion_date']

    def __str__(self):
        return f"Виконано '{self.rule.name}' для {self.truck.license_plate}"