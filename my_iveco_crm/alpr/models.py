from django.db import models
from django.contrib.auth.models import User


def normalize_plate(plate: str) -> str:
    """Нормалізує номерний знак: верхній регістр, без пробілів."""
    return plate.upper().replace(' ', '').strip()


class IgnoredVehicle(models.Model):
    REASON_CHOICES = [
        ('staff', 'Персонал СТО'),
        ('delivery', 'Доставка запчастин'),
        ('neighbor', 'Сусідня організація'),
        ('other', 'Інше'),
    ]

    license_plate = models.CharField(
        max_length=20, unique=True, verbose_name="Держномер",
        help_text="Буде збережено у верхньому регістрі без пробілів"
    )
    reason_type = models.CharField(
        max_length=20, choices=REASON_CHOICES, default='other',
        verbose_name="Категорія"
    )
    description = models.CharField(
        max_length=255, blank=True, verbose_name="Опис",
        help_text="Наприклад: Форд Транзит — Автолідер запчастини"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активний")
    added_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Додав"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Додано")

    class Meta:
        verbose_name = "Ігнорований автомобіль"
        verbose_name_plural = "Список ігнору"
        ordering = ['reason_type', 'license_plate']

    def save(self, *args, **kwargs):
        self.license_plate = normalize_plate(self.license_plate)
        super().save(*args, **kwargs)

    def __str__(self):
        label = self.get_reason_type_display()
        desc = f" — {self.description}" if self.description else ""
        return f"{self.license_plate} [{label}]{desc}"


class VehicleArrival(models.Model):
    license_plate = models.CharField(max_length=20, verbose_name="Розпізнаний номер")
    detected_at = models.DateTimeField(auto_now_add=True, verbose_name="Час заїзду")
    camera_id = models.CharField(max_length=100, blank=True, verbose_name="ID камери")
    confidence = models.FloatField(null=True, blank=True, verbose_name="Впевненість (%)")

    # Знайдені відповідники
    truck = models.ForeignKey(
        'clients.Truck', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='arrivals', verbose_name="Автомобіль"
    )
    client = models.ForeignKey(
        'clients.Client', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='arrivals', verbose_name="Клієнт"
    )
    appointment = models.ForeignKey(
        'appointments.Appointment', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='arrivals', verbose_name="Запис на СТО"
    )

    # Статус обробки
    ignored = models.BooleanField(default=False, verbose_name="Ігнорований")
    ignore_reason = models.CharField(max_length=100, blank=True, verbose_name="Причина ігнору")
    notified = models.BooleanField(default=False, verbose_name="Сповіщення надіслано")

    class Meta:
        verbose_name = "Заїзд автомобіля"
        verbose_name_plural = "Журнал заїздів"
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['license_plate']),
            models.Index(fields=['detected_at']),
        ]

    def __str__(self):
        client_str = f" | {self.client.name}" if self.client else " | невідомий"
        return f"{self.license_plate}{client_str} — {self.detected_at.strftime('%d.%m.%Y %H:%M')}"
