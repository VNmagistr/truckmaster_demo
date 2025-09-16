# clients/models.py

from django.db import models

class IvecoBaseModel(models.Model):
    """
    ДОВІДНИК базових моделей (родин) Iveco.
    Використовується для правил регламенту та для групування вантажівок.
    Приклади: 'Daily', 'Eurocargo', 'Stralis'.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва базової моделі")

    class Meta:
        verbose_name = "Базова модель Iveco"
        verbose_name_plural = "Базові моделі Iveco"

    def __str__(self):
        return self.name

class Client(models.Model):
    """
    Інформація про клієнта (фізична або юридична особа).
    """
    name = models.CharField(max_length=255, verbose_name="Ім'я / Назва компанії")
    surname = models.CharField(max_length=255, blank=True, verbose_name="Прізвище (для фіз. осіб)")
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="Основний номер телефону")
    email = models.EmailField(blank=True, verbose_name="Електронна пошта")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата реєстрації")

    class Meta:
        verbose_name = "Клієнт"
        verbose_name_plural = "Клієнти"

    def __str__(self):
        return f"{self.name} {self.surname}".strip()

class Truck(models.Model):
    """
    Конкретний автомобіль, що належить клієнту.
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Власник")
    base_model = models.ForeignKey(
        IvecoBaseModel,
        on_delete=models.PROTECT,
        verbose_name="Базова модель (родина)"
    )
    specific_model_name = models.CharField(
        max_length=100,
        verbose_name="Точна назва моделі/модифікації",
        help_text="Напр., 70C14 M.Y.2009"
    )
    full_vin = models.CharField(max_length=17, unique=True, verbose_name="Повний VIN-код")
    last_seven_vin = models.CharField(max_length=7, unique=True, blank=True, verbose_name="Останні 7 знаків VIN")
    license_plate = models.CharField(max_length=20, verbose_name="Державний номер")
    year_of_manufacture = models.PositiveIntegerField(verbose_name="Рік випуску")
    current_mileage = models.PositiveIntegerField(default=0, verbose_name="Поточний пробіг (км)")

    class TransmissionChoices(models.TextChoices):
        MANUAL = 'manual', 'Механічна'
        AUTOMATIC = 'automatic', 'Автоматична'
        ROBOT = 'robot', 'Робот'

    transmission_type = models.CharField(max_length=10, choices=TransmissionChoices.choices, verbose_name="Тип КПП")

    class EmissionStandardChoices(models.TextChoices):
        UNKNOWN = 'unknown', 'Не вказано'
        EURO3 = 'euro3', 'Євро-3'
        EURO4 = 'euro4', 'Євро-4'
        EURO5 = 'euro5', 'Євро-5'
        EURO6 = 'euro6', 'Євро-6'

    emission_standard = models.CharField(
        max_length=10,
        choices=EmissionStandardChoices.choices,
        default=EmissionStandardChoices.UNKNOWN,
        verbose_name="Стандарт викидів"
    )

    class Meta:
        verbose_name = "Вантажівка"
        verbose_name_plural = "Вантажівки"

    def save(self, *args, **kwargs):
        self.last_seven_vin = self.full_vin[-7:]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.specific_model_name} ({self.license_plate})"