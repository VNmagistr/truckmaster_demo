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
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Клієнт")
    vin_code = models.CharField(max_length=17, unique=True, verbose_name="VIN-код")
    model = models.CharField(max_length=100, verbose_name="Модель")
    license_plate = models.CharField(max_length=20, verbose_name="Держномер")
    year_of_manufacture = models.PositiveIntegerField(verbose_name="Рік випуску")
    current_mileage = models.PositiveIntegerField(default=0, verbose_name="Поточний пробіг (км)") 

    def __str__(self):
        return f"Iveco {self.model} ({self.license_plate})"