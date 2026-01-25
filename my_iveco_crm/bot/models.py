from django.db import models
from clients.models import Client, Truck

class BotUser(models.Model):
    ROLE_CHOICES = [
        ('guest', 'Гість'),
        ('owner', 'Власник'),
        ('admin', 'Адміністратор'),
    ]

    telegram_id = models.BigIntegerField(unique=True, verbose_name="Telegram ID")
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name="Username")
    first_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ім'я")
    last_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Прізвище")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")
    language_code = models.CharField(max_length=10, default='uk', verbose_name="Мова")
    
    # Тільки клієнт, ніяких працівників
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Клієнт")
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='guest', verbose_name="Роль")
    is_active = models.BooleanField(default=True, verbose_name="Активний")
    is_blocked = models.BooleanField(default=False, verbose_name="Заблокований")
    
    assigned_trucks = models.ManyToManyField(Truck, blank=True, verbose_name="Закріплені авто")
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} ({self.get_role_display()})"

    class Meta:
        verbose_name = "Користувач бота"
        verbose_name_plural = "Користувачі бота"


class BotMessageLog(models.Model):
    bot_user = models.ForeignKey(BotUser, on_delete=models.CASCADE, verbose_name="Користувач")
    message_type = models.CharField(max_length=50, default='text')
    is_incoming = models.BooleanField(default=True, verbose_name="Вхідне?")
    message_text = models.TextField(blank=True, verbose_name="Текст")
    bot_response = models.TextField(blank=True, verbose_name="Відповідь бота")
    created_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Лог повідомлення"
        verbose_name_plural = "Логи повідомлень"


class ReminderSettings(models.Model):
    """Налаштування нагадувань для користувача"""
    bot_user = models.ForeignKey(BotUser, on_delete=models.CASCADE, verbose_name="Користувач")
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, verbose_name="Вантажівка")
    reminder_type = models.CharField(max_length=50, default='maintenance', verbose_name="Тип нагадування") 
    is_enabled = models.BooleanField(default=True, verbose_name="Увімкнено")
    
    class Meta:
        unique_together = ['bot_user', 'truck', 'reminder_type']
        verbose_name = "Налаштування нагадування"
        verbose_name_plural = "Налаштування нагадувань"