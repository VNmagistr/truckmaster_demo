from django.db import models

class Client(models.Model):
    """
    Модель для зберігання інформації про клієнтів (власників вантажівок).
    """
    name = models.CharField(max_length=255, verbose_name="Ім'я / Назва компанії")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    email = models.EmailField(blank=True, verbose_name="Електронна пошта")
    address = models.CharField(max_length=255, blank=True, verbose_name="Адреса")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення")

    def __str__(self):
        return self.name

class Truck(models.Model):
    TRANSMISSION_CHOICES = [
        ('MANUAL', 'Ручна'),
        ('AUTOMATIC', 'Автоматична'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Клієнт")
    
    # Поле для повного VIN-коду
    full_vin = models.CharField(max_length=17, unique=True, verbose_name="Повний VIN-код")
    # Поле, що заповнюється автоматично останніми 7 символами
    last_seven_vin = models.CharField(max_length=7, blank=True, verbose_name="Останні 7 символів VIN")
    model = models.CharField(max_length=100, verbose_name="Модель")
    license_plate = models.CharField(max_length=20, verbose_name="Держномер")
    year_of_manufacture = models.PositiveIntegerField(verbose_name="Рік випуску")
    current_mileage = models.PositiveIntegerField(default=0, verbose_name="Поточний пробіг (км)")
    transmission_type = models.CharField(
        max_length=10,
        choices=TRANSMISSION_CHOICES,
        default='MANUAL',
        verbose_name="Тип трансмісії"
    )

    def __str__(self):
        return f"Iveco {self.model} ({self.license_plate})"

    def save(self, *args, **kwargs):
        # Логіка автоматичного заповнення останніх 7 символів VIN-коду
        if self.full_vin and len(self.full_vin) >= 7:
            self.last_seven_vin = self.full_vin[-7:]
        super().save(*args, **kwargs)