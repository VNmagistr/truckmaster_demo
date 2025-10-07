from django.db import models
from django.db.models import Sum, F
from clients.models import Client, Truck, IvecoBaseModel
from inventory.models import UsedPart

def get_repair_photo_path(instance, filename):
    return f'order_photos/repair/order_{instance.service_order.id}/{filename}'

class RepairPhoto(models.Model):
    service_order = models.ForeignKey('ServiceOrder', on_delete=models.CASCADE, related_name="repair_photos")
    image = models.ImageField(upload_to=get_repair_photo_path, verbose_name="Фото ремонту")
    caption = models.CharField(max_length=255, blank=True, verbose_name="Короткий опис")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Фото для замовлення №{self.service_order.id}"

class WorkCategory(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Назва категорії робіт")
    class Meta:
        verbose_name = "Категорія робіт"
        verbose_name_plural = "Категорії робіт"
    def __str__(self):
        return self.name

class Work(models.Model):
    category = models.ForeignKey(WorkCategory, on_delete=models.CASCADE, related_name="works", verbose_name="Категорія")
    name = models.CharField(max_length=255, verbose_name="Назва роботи")
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Вартість нормогодини (грн)")
    class Meta:
        verbose_name = "Робота з прайсу"
        verbose_name_plural = "Роботи з прайсу"
        unique_together = ('category', 'name')
    def __str__(self):
        return f"{self.category.name} - {self.name}"

class Employee(models.Model):
    name = models.CharField(max_length=255, verbose_name="Ім'я та прізвище")
    position = models.CharField(max_length=100, verbose_name="Посада")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Номер телефону")
    class Meta:
        verbose_name = "Працівник"
        verbose_name_plural = "Працівники"
    def __str__(self):
        return self.name

class ServiceOrder(models.Model):
    order_number = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Номер наряду-замовлення")
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, verbose_name="Автомобіль")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Клієнт")
    car_photo = models.ImageField(upload_to='order_photos/cars/', null=True, blank=True, verbose_name="Фото авто з держномером")
    odometer_photo = models.ImageField(upload_to='order_photos/odometers/', null=True, blank=True, verbose_name="Фото щитка приладів")
    class StatusChoices(models.TextChoices):
        NEW = 'new', 'Нове'
        IN_PROGRESS = 'in_progress', 'В роботі'
        COMPLETED = 'completed', 'Завершено'
        CANCELED = 'canceled', 'Скасовано'
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.NEW, verbose_name="Статус")
    start_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата відкриття")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата закриття")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Загальна вартість")
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            last_order = ServiceOrder.objects.order_by('id').last()
            if last_order and last_order.order_number and last_order.order_number.isdigit():
                next_number = int(last_order.order_number) + 1
            else:
                # Починаємо з 1001, щоб номери були солідніші
                last_id = last_order.id if last_order else 0
                next_number = 1001 + last_id
            self.order_number = str(next_number)
        super().save(*args, **kwargs)

    def update_total_cost(self):
        works_cost = self.works.aggregate(total=Sum('cost'))['total'] or 0
        parts_cost = UsedPart.objects.filter(service_work__service_order=self).aggregate(total=Sum(F('quantity') * F('part__price'), output_field=models.DecimalField()))['total'] or 0
        self.total_cost = works_cost + parts_cost
        self.save(update_fields=['total_cost'])

    class Meta:
        verbose_name = "Замовлення-наряд"
        verbose_name_plural = "Замовлення-наряди"
        ordering = ['-start_date']
    def __str__(self):
        return f"Замовлення №{self.order_number or self.id} для {self.truck.license_plate}"

class ServiceWork(models.Model):
    service_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name="works", verbose_name="Замовлення-наряд")
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Виконавець")
    work = models.ForeignKey(Work, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Виконана робота")
    custom_description = models.CharField(max_length=255, blank=True, verbose_name="Опис/уточнення")
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Фактична вартість")
    duration_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Витрачено годин")
    def save(self, *args, **kwargs):
        if self.work and self.duration_hours > 0:
             self.cost = self.work.price_per_hour * self.duration_hours
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = "Виконана робота"
        verbose_name_plural = "Виконані роботи"
    def __str__(self):
        return f"{self.work.name} для замовлення №{self.service_order.id}"

class MaintenanceRule(models.Model):
    name = models.CharField(max_length=255, verbose_name="Назва регламентної роботи")
    interval_km = models.PositiveIntegerField(verbose_name="Інтервал пробігу (км)")
    applicable_models = models.ManyToManyField(IvecoBaseModel, verbose_name="Застосовується до базових моделей")
    class TransmissionChoices(models.TextChoices):
        ANY = 'any', 'Будь-яка'
        MANUAL = 'manual', 'Механічна'
        AUTOMATIC = 'automatic', 'Автоматична'
        ROBOT = 'robot', 'Робот'
    applicable_transmission = models.CharField(max_length=10, choices=TransmissionChoices.choices, default=TransmissionChoices.ANY, verbose_name="Застосовується до типу КПП")
    class Meta:
        verbose_name = "Правило регламенту"
        verbose_name_plural = "Правила регламентів"
    def __str__(self):
        return f"{self.name} (кожні {self.interval_km} км)"

class MaintenanceLog(models.Model):
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