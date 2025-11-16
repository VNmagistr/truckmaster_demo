from django.db import models

class Client(models.Model):
    name = models.CharField(max_length=255, verbose_name="Ім'я")
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="Основний номер телефону")
    email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    telegram_chat_id = models.BigIntegerField(unique=True, blank=True, null=True, db_index=True, verbose_name="ID чату Telegram")
    
    class Meta:
        verbose_name = "Клієнт"
        verbose_name_plural = "Клієнти"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class IvecoBaseModel(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Базова модель")
    
    class Meta:
        verbose_name = "Базова модель Iveco"
        verbose_name_plural = "Базові моделі Iveco"
    
    def __str__(self):
        return self.name

class Truck(models.Model):
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Власник")
    base_model = models.ForeignKey(IvecoBaseModel, on_delete=models.SET_NULL, null=True, verbose_name="Базова модель")
    specific_model_name = models.CharField(max_length=100, verbose_name="Конкретна модель (напр. 35C15)")
    full_vin = models.CharField(max_length=17, unique=True, verbose_name="Повний VIN")
    last_seven_vin = models.CharField(max_length=7, unique=True, db_index=True, verbose_name="Останні 7 символів VIN")
    license_plate = models.CharField(max_length=20, verbose_name="Номерний знак", db_index=True)
    
    class Meta:
        verbose_name = "Вантажівка"
        verbose_name_plural = "Вантажівки"
        ordering = ['license_plate']
    
    def __str__(self):
        return f"{self.specific_model_name} ({self.license_plate})"

    # --- НОВА ЛОГІКА ДЛЯ ЗБЕРЕЖЕННЯ ІСТОРІЇ ---
    def save(self, *args, **kwargs):
        if self.pk: # Якщо це оновлення існуючого об'єкта
            try:
                # Отримуємо стару версію з бази даних
                old_version = Truck.objects.get(pk=self.pk)
                
                # Перевіряємо, чи змінилися ключові поля
                client_changed = old_version.client_id != self.client_id
                plate_changed = old_version.license_plate != self.license_plate

                if client_changed or plate_changed:
                    # Логуємо *старі* значення
                    OwnershipHistory.objects.create(
                        truck=self,
                        client=old_version.client, # Зберігаємо *попереднього* клієнта
                        license_plate=old_version.license_plate # Зберігаємо *попередній* номер
                    )
            except Truck.DoesNotExist:
                # Об'єкт ще не в базі, нічого не робимо
                pass 
        
        # Запускаємо стандартний процес збереження (зберігаємо нові дані)
        super().save(*args, **kwargs)

# --- НОВА МОДЕЛЬ ДЛЯ ІСТОРІЇ ---
class OwnershipHistory(models.Model):
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name="ownership_history", verbose_name="Вантажівка")
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Попередній власник")
    license_plate = models.CharField(max_length=20, verbose_name="Попередній номерний знак")
    change_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата зміни")
    
    class Meta:
        verbose_name = "Запис історії"
        verbose_name_plural = "Історія володіння"
        ordering = ['-change_date'] # Сортуємо від нових до старих

    def __str__(self):
        # Використовуємо last_seven_vin для чіткості, оскільки VIN - це наш ключ
        return f"{self.truck.last_seven_vin} - {self.client.name if self.client else 'N/A'} ({self.license_plate}) - {self.change_date.strftime('%Y-%m-%d')}"