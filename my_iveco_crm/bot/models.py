# bot/models.py
from django.db import models
from clients.models import Client, Truck


class BotUser(models.Model):
    """
    Користувач Telegram бота з ролями
    """
    ROLE_CHOICES = [
        ('admin', 'Адміністратор'),
        ('owner', 'Власник'),
        ('driver', 'Водій'),
        ('guest', 'Гість'),
    ]

    chat_id = models.BigIntegerField(unique=True, db_index=True, verbose_name="Chat ID")
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name="Username Telegram")
    first_name = models.CharField(max_length=255, blank=True, verbose_name="Ім'я")
    last_name = models.CharField(max_length=255, blank=True, verbose_name="Прізвище")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Номер телефону")
    
    # Роль користувача
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='guest',
        verbose_name="Роль"
    )
    
    # Прив'язка до клієнта (для власників)
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bot_users',
        verbose_name="Клієнт"
    )
    
    # Доступні вантажівки (для водіїв)
    allowed_trucks = models.ManyToManyField(
        Truck,
        blank=True,
        related_name='bot_users',
        verbose_name="Доступні вантажівки"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Активний")
    is_blocked = models.BooleanField(default=False, verbose_name="Заблокований")
    
    # Налаштування сповіщень
    notifications_enabled = models.BooleanField(default=True, verbose_name="Сповіщення увімкнено")
    notify_order_status = models.BooleanField(default=True, verbose_name="Сповіщення про статус замовлення")
    notify_maintenance = models.BooleanField(default=True, verbose_name="Сповіщення про ТО")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата реєстрації")
    last_activity = models.DateTimeField(auto_now=True, verbose_name="Остання активність")
    
    class Meta:
        verbose_name = "Користувач бота"
        verbose_name_plural = "Користувачі бота"
        ordering = ['-last_activity']
    
    def __str__(self):
        name = self.first_name or self.username or f"ID: {self.chat_id}"
        return f"{name} ({self.get_role_display()})"
    
    @property
    def full_name(self):
        """Повне ім'я користувача"""
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts)) or self.username or f"User {self.chat_id}"
    
    def can_view_truck(self, truck):
        """Чи може користувач переглядати цю вантажівку"""
        if self.role == 'admin':
            return True
        if self.role == 'owner' and self.client:
            return truck.client == self.client
        if self.role == 'driver':
            return self.allowed_trucks.filter(pk=truck.pk).exists()
        return False
    
    def can_view_order(self, order):
        """Чи може користувач переглядати це замовлення"""
        if self.role == 'admin':
            return True
        if self.role == 'owner' and self.client:
            return order.client == self.client
        if self.role == 'driver' and order.truck:
            return self.allowed_trucks.filter(pk=order.truck.pk).exists()
        return False
    
    def get_accessible_trucks(self):
        """Отримати список доступних вантажівок"""
        if self.role == 'admin':
            return Truck.objects.all()
        if self.role == 'owner' and self.client:
            return Truck.objects.filter(client=self.client)
        if self.role == 'driver':
            return self.allowed_trucks.all()
        return Truck.objects.none()


class BotMessageLog(models.Model):
    """Лог повідомлень бота"""
    chat_id = models.BigIntegerField(db_index=True)
    user_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Номер телефону")
    message_text = models.TextField(verbose_name="Повідомлення від користувача")
    bot_response = models.TextField(verbose_name="Відповідь бота")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Час")

    class Meta:
        verbose_name = "Лог повідомлення"
        verbose_name_plural = "Логи повідомлень"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user_name} (ID: {self.chat_id}) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"