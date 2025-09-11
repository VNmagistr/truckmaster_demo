from django.db import models
from orders.models import ServiceWork

class Part(models.Model):
    """
    Модель для обліку запчастин на складі.
    """
    GROUP_CHOICES = [
        ('ENGINE', 'Двигун'),
        ('TRANSMISSION', 'Трансмісія'),
        ('CHASSIS', 'Ходова частина'),
        ('ELECTRICAL', 'Електрика'),
        ('BODY', 'Кузовні деталі'),
        ('UNDEFINED', 'Інше'),
    ]
    name = models.CharField(max_length=255, verbose_name="Назва")
    group = models.CharField(max_length=255, choices=GROUP_CHOICES,
        default='UNDEFINED', blank=True, verbose_name="Група запчастин")
    sku_code = models.CharField(max_length=50, unique=True, verbose_name="Артикул")
    current_stock = models.PositiveIntegerField(default=0, verbose_name="Кількість на складі")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна")
    provider = models.CharField(max_length=255, blank=True, verbose_name="Постачальник")

    def __str__(self):
        return self.name

class UsedPart(models.Model):
    """
    Проміжна модель для зв'язку між роботами та використаними запчастинами.
    """
    service_work = models.ForeignKey(ServiceWork, on_delete=models.CASCADE, verbose_name="Виконана робота")
    part = models.ForeignKey(Part, on_delete=models.CASCADE, verbose_name="Запчастина")
    quantity = models.PositiveIntegerField(verbose_name="Кількість")

    def __str__(self):
        return f"{self.quantity} x {self.part.name} для {self.service_work.job_description}"