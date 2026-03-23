from django.db import models
from django.db.models import Max
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator

class Client(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='client_profile',
        verbose_name="Акаунт клієнта"
    )
    name = models.CharField(max_length=255, verbose_name="Ім'я")
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="Основний номер телефону")
    email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    telegram_chat_id = models.BigIntegerField(unique=True, blank=True, null=True, db_index=True, verbose_name="ID чату Telegram")
    is_admin = models.BooleanField(default=False, verbose_name="Адміністратор бота")
    # Поля для м'якого видалення
    marked_for_deletion = models.BooleanField(
        default=False, 
        verbose_name="Позначено на видалення"
    )
    marked_for_deletion_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients_marked_for_deletion',
        verbose_name="Позначив на видалення"
    )
    marked_for_deletion_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата позначення"
    )
    deletion_reason = models.TextField(
        blank=True,
        verbose_name="Причина видалення"
    )
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
        ordering = ['name']

    def __str__(self):
        return self.name

class Truck(models.Model):
    EURO_STANDARD_CHOICES = [
        ('EURO3', 'Євро-3'),
        ('EURO4', 'Євро-4'),
        ('EURO5', 'Євро-5'),
        ('EURO6', 'Євро-6'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Власник")
    base_model = models.ForeignKey(IvecoBaseModel, on_delete=models.SET_NULL, null=True, verbose_name="Базова модель")
    specific_model_name = models.CharField(max_length=100, verbose_name="Конкретна модель (напр. 35C15)")
    full_vin = models.CharField(max_length=17, unique=True, verbose_name="Повний VIN", validators=[MinLengthValidator(17)])
    last_seven_vin = models.CharField(max_length=7, db_index=True, verbose_name="Останні 7 символів VIN", editable=False)
    license_plate = models.CharField(max_length=20, verbose_name="Номерний знак")
    euro_standard = models.CharField(max_length=10, choices=EURO_STANDARD_CHOICES, blank=True, null=True, verbose_name="Євростандарт викидів")
    # Поля для м'якого видалення
    marked_for_deletion = models.BooleanField(
        default=False, 
        verbose_name="Позначено на видалення"
    )
    marked_for_deletion_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trucks_marked_for_deletion',
        verbose_name="Позначив на видалення"
    )
    marked_for_deletion_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата позначення"
    )
    deletion_reason = models.TextField(
        blank=True,
        verbose_name="Причина видалення"
    )
    
    class Meta:
        verbose_name = "Вантажівка"
        verbose_name_plural = "Вантажівки"
        ordering = ['license_plate']
        indexes = [
            models.Index(fields=['license_plate']),
            models.Index(fields=['last_seven_vin']),
            models.Index(fields=['client', 'license_plate']),
        ]

    def __str__(self):
        euro = f" ({self.get_euro_standard_display()})" if self.euro_standard else ""
        return f"{self.specific_model_name} ({self.license_plate}){euro}"

    def save(self, *args, **kwargs):
        # Автоматично витягуємо останні 7 символів з VIN
        if self.full_vin:
            self.last_seven_vin = self.full_vin[-7:]
        
        # Зберігаємо історію зміни власника
        if self.pk: 
            try:
                old_version = Truck.objects.get(pk=self.pk)
                client_changed = old_version.client_id != self.client_id
                plate_changed = old_version.license_plate != self.license_plate

                if client_changed or plate_changed:
                    OwnershipHistory.objects.create(
                        truck=self,
                        client=old_version.client, 
                        license_plate=old_version.license_plate 
                    )
            except Truck.DoesNotExist:
                pass 
        
        super().save(*args, **kwargs)

    def get_latest_mileage(self):
        """Отримує останній зафіксований пробіг (з замовлень або звітів бота)."""
        from orders.models import ServiceOrder
        from bot.models import MileageReport

        order_mileage = ServiceOrder.objects.filter(
            truck=self
        ).aggregate(Max('current_mileage'))['current_mileage__max'] or 0

        report_mileage = MileageReport.objects.filter(
            truck=self
        ).aggregate(Max('mileage'))['mileage__max'] or 0

        return max(order_mileage, report_mileage)

# --- ДОСТУП ДО ФУНКЦІЙ ---

class ClientFeature(models.Model):
    """
    Індивідуальний доступ клієнта до функцій системи.
    Створюється автоматично разом з Client.
    """
    client = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name='features',
        verbose_name='Клієнт',
    )
    cabinet = models.BooleanField(
        default=True, verbose_name='Особистий кабінет',
        help_text='Доступ до /cabinet/ — перегляд замовлень та авто.',
    )
    bot = models.BooleanField(
        default=False, verbose_name='Telegram бот',
        help_text='Участь у Telegram боті (звіти пробігу, команди).',
    )
    invoices = models.BooleanField(
        default=False, verbose_name='Рахунки',
        help_text='Перегляд виставлених рахунків на запчастини.',
    )
    appointments = models.BooleanField(
        default=False, verbose_name='Онлайн-запис',
        help_text='Самостійний запис на СТО через кабінет.',
    )
    notifications_telegram = models.BooleanField(
        default=False, verbose_name='Сповіщення Telegram',
        help_text='Надсилати Telegram-сповіщення при додаванні фото ремонту.',
    )
    notifications_whatsapp = models.BooleanField(
        default=False, verbose_name='Сповіщення WhatsApp',
        help_text='Надсилати WhatsApp-сповіщення при додаванні фото ремонту.',
    )

    class Meta:
        verbose_name = 'Доступ до функцій'
        verbose_name_plural = 'Доступ до функцій'

    def __str__(self):
        return f'Функції: {self.client.name}'


# --- МОДЕЛЬ ДЛЯ ІСТОРІЇ ---
class OwnershipHistory(models.Model):
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name="ownership_history", verbose_name="Вантажівка")
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Попередній власник")
    license_plate = models.CharField(max_length=20, verbose_name="Попередній номерний знак")
    change_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата зміни")
    
    class Meta:
        verbose_name = "Запис історії"
        verbose_name_plural = "Історія володіння"
        ordering = ['-change_date'] 

    def __str__(self):
        return f"{self.truck.last_seven_vin} - {self.client.name if self.client else 'N/A'} ({self.license_plate}) - {self.change_date.strftime('%Y-%m-%d')}"