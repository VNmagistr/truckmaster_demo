# inventory/models.py

from django.db import models
from orders.models import ServiceWork

class Part(models.Model):
    """
    Запчастина на складі.
    """
    name = models.CharField(max_length=255, verbose_name="Назва запчастини")
    sku_code = models.CharField(max_length=100, unique=True, verbose_name="Артикул")
    current_stock = models.PositiveIntegerField(default=0, verbose_name="Кількість на складі")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна продажу")

    class Meta:
        verbose_name = "Запчастина"
        verbose_name_plural = "Запчастини"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku_code})"

class UsedPart(models.Model):
    """
    Проміжна модель, що фіксує, яка запчастина і в якій кількості
    була використана для конкретної роботи.
    """
    service_work = models.ForeignKey(ServiceWork, on_delete=models.CASCADE, related_name="used_parts", verbose_name="Робота")
    part = models.ForeignKey(Part, on_delete=models.PROTECT, verbose_name="Запчастина")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Кількість")
    
    class Meta:
        verbose_name = "Використана запчастина"
        verbose_name_plural = "Використані запчастини"
        unique_together = ('service_work', 'part') # Уникаємо дублювання однієї і тієї ж запчастини в одній роботі

    def __str__(self):
        return f"{self.quantity} x {self.part.name} для роботи '{self.service_work.job_description}'"