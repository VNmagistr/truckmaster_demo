# bot/models.py

from django.db import models
from django.utils import timezone


class BotSettings(models.Model):
    """
    Глобальні налаштування бота (singleton - один запис)
    """
    maintenance_reminders_enabled = models.BooleanField(
        'Увімкнути нагадування про ТО',
        default=False,
        help_text='Глобальний перемикач для всієї системи нагадувань'
    )
    reminder_days_before = models.PositiveIntegerField(
        'За скільки днів нагадувати (для дат)',
        default=7,
        help_text='Нагадування за X днів до планової дати'
    )
    reminder_km_before = models.PositiveIntegerField(
        'За скільки км нагадувати',
        default=1000,
        help_text='Попередження за X км до планового ТО'
    )
    reminder_time = models.TimeField(
        'Час відправки нагадувань',
        default='09:00',
        help_text='О котрій годині надсилати нагадування'
    )
    last_check = models.DateTimeField(
        'Остання перевірка',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'Налаштування бота'
        verbose_name_plural = 'Налаштування бота'
    
    def __str__(self):
        status = '✅ Увімкнено' if self.maintenance_reminders_enabled else '❌ Вимкнено'
        return f'Налаштування бота - Нагадування: {status}'
    
    def save(self, *args, **kwargs):
        # Singleton pattern - тільки один запис
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Отримати налаштування (або створити з defaults)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class BotUser(models.Model):
    """Користувачі Telegram бота"""
    
    ROLE_CHOICES = [
        ('admin', 'Адміністратор'),
        ('owner', 'Власник'),
        ('driver', 'Водій'),
        ('guest', 'Гість'),
    ]
    
    chat_id = models.BigIntegerField(
        'Chat ID',
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        help_text='Telegram chat_id користувача'
    )
    username = models.CharField(
        'Username',
        max_length=255,
        blank=True,
        help_text='Telegram username (@username)'
    )
    first_name = models.CharField("Ім'я", max_length=255)
    last_name = models.CharField('Прізвище', max_length=255, blank=True)
    phone_number = models.CharField(
        'Номер телефону',
        max_length=20,
        blank=True,
        help_text='У форматі +380...'
    )
    
    role = models.CharField(
        'Роль',
        max_length=20,
        choices=ROLE_CHOICES,
        default='guest'
    )
    
    # Прив'язка до клієнта (для власників)
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Клієнт',
        help_text='Для власників - прив\'язка до картки клієнта'
    )
    
    # Доступні вантажівки (для водіїв)
    allowed_trucks = models.ManyToManyField(
        'clients.Truck',
        blank=True,
        verbose_name='Доступні вантажівки',
        help_text='Для водіїв - до яких вантажівок має доступ'
    )
    
    # Налаштування нагадувань
    enable_maintenance_reminders = models.BooleanField(
        'Увімкнути нагадування про ТО',
        default=True,
        help_text='Чи надсилати цьому користувачу нагадування про ТО'
    )
    reminder_telegram_enabled = models.BooleanField(
        'Telegram нагадування',
        default=True,
        help_text='Надсилати нагадування в Telegram'
    )
    
    # Статус
    is_active = models.BooleanField('Активний', default=True)
    is_blocked = models.BooleanField('Заблокований', default=False)
    
    notes = models.TextField('Примітки', blank=True)
    
    created_at = models.DateTimeField('Створено', auto_now_add=True)
    last_activity = models.DateTimeField('Остання активність', auto_now=True)
    
    class Meta:
        verbose_name = 'Користувач бота'
        verbose_name_plural = 'Користувачі бота'
        ordering = ['-created_at']
    
    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return f"{name} ({self.get_role_display()})"
    
    def get_role_emoji(self):
        """Повертає емодзі для ролі"""
        emojis = {
            'admin': '👑',
            'owner': '👤',
            'driver': '🚗',
            'guest': '👻'
        }
        return emojis.get(self.role, '❓')
    
    def get_accessible_trucks(self):
        """Повертає список вантажівок доступних користувачу"""
        from clients.models import Truck
        
        if self.role == 'admin':
            return Truck.objects.all()
        elif self.role == 'owner' and self.client:
            return Truck.objects.filter(client=self.client)
        elif self.role == 'driver':
            return self.allowed_trucks.all()
        else:
            return Truck.objects.none()
    
    def can_view_truck(self, truck):
        """Перевіряє чи може користувач бачити цю вантажівку"""
        if self.role == 'admin':
            return True
        elif self.role == 'owner' and self.client:
            return truck.client == self.client
        elif self.role == 'driver':
            return self.allowed_trucks.filter(pk=truck.pk).exists()
        return False
    
    def can_view_order(self, order):
        """Перевіряє чи може користувач бачити це замовлення"""
        if self.role == 'admin':
            return True
        elif self.role == 'owner' and self.client:
            return order.client == self.client
        elif self.role == 'driver':
            return order.truck and self.allowed_trucks.filter(pk=order.truck.pk).exists()
        return False


class BotMessageLog(models.Model):
    """Журнал повідомлень бота"""
    
    chat_id = models.BigIntegerField(db_index=True)
    user_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name="Номер телефону"
    )
    message_text = models.TextField(verbose_name="Повідомлення від користувача")
    bot_response = models.TextField(verbose_name="Відповідь бота")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Час")

    class Meta:
        verbose_name = "Лог повідомлення"
        verbose_name_plural = "Логи повідомлень"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user_name} (ID: {self.chat_id}) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class SentReminder(models.Model):
    """
    Журнал відправлених нагадувань про ТО
    """
    REMINDER_TYPE_CHOICES = [
        ('warning', 'Попередження (за 1000 км)'),
        ('urgent', 'Термінове (досягнуто інтервалу)'),
    ]
    
    DELIVERY_STATUS_CHOICES = [
        ('sent', 'Надіслано'),
        ('delivered', 'Доставлено'),
        ('failed', 'Помилка'),
    ]
    
    bot_user = models.ForeignKey(
        BotUser,
        on_delete=models.CASCADE,
        verbose_name='Користувач'
    )
    truck = models.ForeignKey(
        'clients.Truck',
        on_delete=models.CASCADE,
        verbose_name='Вантажівка'
    )
    reminder_type = models.CharField(
        max_length=20,
        choices=REMINDER_TYPE_CHOICES,
        verbose_name='Тип нагадування'
    )
    service_reminder = models.ForeignKey(
        'maintenance.ServiceReminder',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Нагадування про ТО'
    )
    sent_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Відправлено'
    )
    delivery_status = models.CharField(
        max_length=20,
        choices=DELIVERY_STATUS_CHOICES,
        default='sent',
        verbose_name='Статус доставки'
    )
    error_message = models.TextField(
        'Повідомлення про помилку', 
        blank=True
    )
    
    class Meta:
        verbose_name = 'Відправлене нагадування'
        verbose_name_plural = 'Відправлені нагадування'
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.bot_user.first_name} - {self.truck.license_plate} - {self.get_reminder_type_display()}"