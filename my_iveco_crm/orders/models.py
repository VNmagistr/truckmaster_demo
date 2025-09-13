from django.db import models
from clients.models import Client, Truck, IvecoModel

class Employee(models.Model):
    """
    Модель для зберігання інформації про працівників СТО.
    """
    name = models.CharField(max_length=255, verbose_name="Ім'я")
    position = models.CharField(max_length=100, verbose_name="Посада")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")

    class Meta:
        verbose_name = "Працівник"
        verbose_name_plural = "Працівники"

    def __str__(self):
        return self.name

class ServiceOrder(models.Model):
    """
    Модель для обліку замовлень-нарядів.
    """
    STATUS_CHOICES = [
        ('IN_PROGRESS', 'В роботі'),
        ('COMPLETED', 'Виконано'),
        ('CANCELED', 'Скасовано'),
        ('PAID', 'Оплачено'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Клієнт")
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, verbose_name="Вантажівка")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS', verbose_name="Статус")
    start_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата початку")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершення")
    description = models.TextField(blank=True, verbose_name="Опис робіт")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Загальна вартість")

    class Meta:
        verbose_name = "Замовлення-наряд"
        verbose_name_plural = "Замовлення-наряди"

    def __str__(self):
        return f"Замовлення №{self.id} для {self.client.name} ({self.truck.license_plate})"

class ServiceWork(models.Model):
    """
    Модель для деталізації робіт в замовленні-наряді.
    """
    service_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, verbose_name="Замовлення-наряд")
    job_description = models.CharField(max_length=255, verbose_name="Назва роботи")
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Вартість робіт")
    duration_hours = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Тривалість (години)")
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Виконавець")

    class Meta:
        verbose_name = "Виконана робота"
        verbose_name_plural = "Виконані роботи"

    def __str__(self):
        return self.job_description

class MaintenanceRule(models.Model):
    """
    Модель для зберігання правил регламентних робіт, 
    з урахуванням типу трансмісії та моделей Iveco.
    """
    name = models.CharField(max_length=255, verbose_name="Назва роботи")
    interval_km = models.PositiveIntegerField(verbose_name="Інтервал пробігу (км)")
    
    TRANSMISSION_CHOICES = [
        ('ALL', 'Для всіх типів'),
        ('MANUAL', 'Ручна'),
        ('ROBOTIC', 'Роботизована'),
        ('AUTOMATIC', 'Автоматична'),
    ]
    applicable_transmission = models.CharField(
        max_length=15,
        choices=TRANSMISSION_CHOICES,
        default='ALL',
        verbose_name="Застосовується до типу трансмісії"
    )

    applicable_models = models.ManyToManyField(
        IvecoModel, 
        blank=True, 
        verbose_name="Застосовується до моделей Iveco",
        help_text="Оберіть моделі Iveco, до яких застосовується це правило. Якщо не обрано жодної, правило застосовується до всіх моделей."
    )

    class Meta:
        verbose_name = "Правило регламенту"
        verbose_name_plural = "Правила регламентів"

    def __str__(self):
        models_str = ", ".join([model.name for model in self.applicable_models.all()])
        if models_str:
            return f"{self.name} ({self.applicable_transmission}) для {models_str} (кожні {self.interval_km} км)"
        return f"{self.name} ({self.applicable_transmission}) для всіх моделей (кожні {self.interval_km} км)"

class MaintenanceLog(models.Model):
    """
    Модель для журналу виконаних регламентних робіт.
    """
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, verbose_name="Вантажівка")
    rule = models.ForeignKey(MaintenanceRule, on_delete=models.CASCADE, verbose_name="Правило")
    completion_date = models.DateField(auto_now_add=True, verbose_name="Дата виконання")
    completion_mileage = models.PositiveIntegerField(verbose_name="Пробіг на момент виконання (км)")

    class Meta:
        verbose_name = "Запис регламенту"
        verbose_name_plural = "Журнал регламентних робіт"

    def __str__(self):
        return f"Виконано {self.rule.name} на {self.truck.license_plate} ({self.completion_date})"