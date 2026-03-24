from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from clients.models import Client


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Очікує підтвердження'),
        ('confirmed', 'Підтверджено'),
        ('cancelled', 'Скасовано'),
        ('completed', 'Завершено'),
        ('no_show', 'Не з\'явився'),
    ]

    SERVICE_TYPE_CHOICES = [
        ('diagnosis', 'Діагностика'),
        ('maintenance', 'Технічне обслуговування'),
        ('repair', 'Ремонт'),
        ('other', 'Інше'),
    ]

    # Client identification
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='appointments', verbose_name="Клієнт (з бази)")
    client_name = models.CharField(max_length=255, verbose_name="Ім'я клієнта")
    client_phone = models.CharField(max_length=20, verbose_name="Телефон клієнта")
    license_plate = models.CharField(max_length=20, verbose_name="Держномер авто")

    # Appointment details
    scheduled_dt = models.DateTimeField(verbose_name="Дата та час запису")
    duration_minutes = models.PositiveIntegerField(default=60, verbose_name="Тривалість (хв)")
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES,
                                    default='repair', verbose_name="Тип послуги")
    description = models.TextField(blank=True, verbose_name="Опис/коментар")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                               default='pending', verbose_name="Статус")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name="Створив")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Створено")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Оновлено")

    # Link to service order if converted
    converted_to_order = models.ForeignKey(
        'orders.ServiceOrder', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='from_appointment',
        verbose_name="Наряд-замовлення"
    )

    # Notification flags
    confirmation_sent = models.BooleanField(default=False, verbose_name="Підтвердження надіслано")
    reminder_sent = models.BooleanField(default=False, verbose_name="Нагадування надіслано")

    class Meta:
        verbose_name = "Запис на СТО"
        verbose_name_plural = "Записи на СТО"
        ordering = ['scheduled_dt']

    def __str__(self):
        return f"{self.client_name} — {self.license_plate} ({timezone.localtime(self.scheduled_dt).strftime('%d.%m.%Y %H:%M')})"

    @property
    def end_dt(self):
        from datetime import timedelta
        return self.scheduled_dt + timedelta(minutes=self.duration_minutes)
