# inventory/models.py

from django.db import models


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
    service_work = models.ForeignKey(
        'orders.ServiceWork', # <-- Ось так, у вигляді рядка 'назва_додатку.НазваМоделі'
        on_delete=models.CASCADE, 
        related_name="used_parts", 
        verbose_name="Робота"
    )
    part = models.ForeignKey(Part, on_delete=models.PROTECT, verbose_name="Запчастина")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Кількість")

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk: # Якщо це оновлення існуючого запису
                old_self = UsedPart.objects.get(pk=self.pk)
                quantity_diff = self.quantity - old_self.quantity
                self.part.current_stock -= quantity_diff
            else: # Якщо це створення нового запису
                self.part.current_stock -= self.quantity

            if self.part.current_stock < 0:
                # Можна додати ValidationError, але поки просто не дамо піти в мінус
                raise Exception(f"Недостатньо запчастин '{self.part.name}' на складі.")

            self.part.save()
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            self.part.current_stock += self.quantity
            self.part.save()
            super().delete(*args, **kwargs)
    
    class Meta:
        verbose_name = "Використана запчастина"
        verbose_name_plural = "Використані запчастини"
        unique_together = ('service_work', 'part') # Уникаємо дублювання однієї і тієї ж запчастини в одній роботі

    def __str__(self):
        return f"{self.quantity} x {self.part.name} для роботи '{self.service_work.job_description}'"