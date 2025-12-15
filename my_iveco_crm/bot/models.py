# bot/models.py

from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator


class BotUser(models.Model):
    """
    Користувач Telegram бота з системою ролей
    """
    ROLE_CHOICES = [
        ('guest', 'Гість'),
        ('driver', 'Водій'),
        ('owner', 'Власник'),
        ('manager', 'Менеджер'),
        ('admin', 'Адміністратор'),
    ]
    
    # Telegram дані
    telegram_id = models.BigIntegerField(
        unique=True,
        db_index=True,
        verbose_name="Telegram ID"
    )
    username = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Username (@username)"
    )
    first_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Ім'я"
    )
    last_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Прізвище"
    )
    
    # Контакти
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Номер телефону має бути в форматі: '+380501234567'"
    )
    phone_number = models.CharField(
        validators=[phone_validator],
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Номер телефону"
    )
    
    # Роль та доступ
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='guest',
        db_index=True,
        verbose_name="Роль"
    )
    
    # Зв'язки з CRM
    client = models.OneToOneField(
        'clients.Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bot_user',
        verbose_name="Клієнт CRM"
    )
    
    # Для водіїв - список автомобілів, якими керує
    assigned_trucks = models.ManyToManyField(
        'clients.Truck',
        blank=True,
        related_name='drivers',
        verbose_name="Закріплені автомобілі (для водія)"
    )
    
    # Статус
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активний"
    )
    is_blocked = models.BooleanField(
        default=False,
        verbose_name="Заблокований"
    )
    block_reason = models.TextField(
        blank=True,
        verbose_name="Причина блокування"
    )
    
    # Налаштування
    language_code = models.CharField(
        max_length=10,
        default='uk',
        verbose_name="Мова"
    )
    notifications_enabled = models.BooleanField(
        default=True,
        verbose_name="Сповіщення увімкнені"
    )
    
    # Статистика
    total_messages = models.IntegerField(
        default=0,
        verbose_name="Всього повідомлень"
    )
    last_activity = models.DateTimeField(
        auto_now=True,
        db_index=True,
        verbose_name="Остання активність"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата реєстрації"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Оновлено"
    )

    class Meta:
        verbose_name = "Користувач бота"
        verbose_name_plural = "Користувачі бота"
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['telegram_id', 'role']),
            models.Index(fields=['phone_number']),
        ]

    def __str__(self):
        name = self.get_full_name()
        role = self.get_role_display()
        return f"{name} ({role})"

    def get_full_name(self):
        """Повертає повне ім'я користувача"""
        parts = [self.first_name, self.last_name]
        full_name = ' '.join(filter(None, parts))
        return full_name or self.username or f"User {self.telegram_id}"

    def increment_message_count(self):
        """Збільшує лічильник повідомлень"""
        self.total_messages += 1
        self.save(update_fields=['total_messages', 'last_activity'])

    def has_permission(self, permission):
        """Перевіряє чи має користувач певний дозвіл"""
        permissions = {
            'guest': ['view_basic_info'],
            'driver': ['view_basic_info', 'view_own_trucks', 'view_maintenance_schedule'],
            'owner': ['view_basic_info', 'view_own_trucks', 'view_maintenance_schedule', 
                     'view_orders', 'view_history', 'request_service'],
            'manager': ['view_basic_info', 'view_all_trucks', 'view_all_orders', 
                       'create_orders', 'send_notifications'],
            'admin': ['all'],
        }
        
        if self.role == 'admin':
            return True
        
        return permission in permissions.get(self.role, [])


class ConversationState(models.Model):
    """
    Стан розмови користувача (FSM - Finite State Machine)
    """
    bot_user = models.OneToOneField(
        BotUser,
        on_delete=models.CASCADE,
        related_name='conversation_state',
        verbose_name="Користувач"
    )
    current_state = models.CharField(
        max_length=100,
        default='idle',
        verbose_name="Поточний стан"
    )
    context_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Контекст розмови"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Оновлено"
    )

    class Meta:
        verbose_name = "Стан розмови"
        verbose_name_plural = "Стани розмов"

    def __str__(self):
        return f"{self.bot_user.get_full_name()} - {self.current_state}"

    def set_state(self, state, context=None):
        """Встановлює новий стан розмови"""
        self.current_state = state
        if context:
            self.context_data.update(context)
        self.save()

    def reset(self):
        """Скидає стан розмови"""
        self.current_state = 'idle'
        self.context_data = {}
        self.save()


class MessageLog(models.Model):
    """
    Лог повідомлень бота - зберігає всю історію комунікації
    """
    MESSAGE_TYPES = [
        ('text', 'Текст'),
        ('command', 'Команда'),
        ('contact', 'Контакт'),
        ('callback', 'Callback кнопка'),
        ('photo', 'Фото'),
        ('document', 'Документ'),
        ('location', 'Локація'),
        ('other', 'Інше'),
    ]
    
    bot_user = models.ForeignKey(
        BotUser,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Користувач"
    )
    
    # Тип та напрямок
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPES,
        default='text',
        verbose_name="Тип повідомлення"
    )
    is_incoming = models.BooleanField(
        default=True,
        verbose_name="Вхідне повідомлення"
    )
    
    # Вміст
    message_text = models.TextField(
        blank=True,
        verbose_name="Текст повідомлення"
    )
    message_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Додаткові дані (JSON)"
    )
    
    # Відповідь бота
    bot_response = models.TextField(
        blank=True,
        verbose_name="Відповідь бота"
    )
    
    # Обробка
    is_processed = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Оброблено"
    )
    processing_time_ms = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Час обробки (мс)"
    )
    handler_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Назва обробника"
    )
    error_message = models.TextField(
        blank=True,
        verbose_name="Повідомлення про помилку"
    )
    
    # Timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Створено"
    )

    class Meta:
        verbose_name = "Лог повідомлення"
        verbose_name_plural = "Логи повідомлень"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at', 'bot_user']),
            models.Index(fields=['is_incoming', 'is_processed']),
        ]

    def __str__(self):
        direction = "➡️" if self.is_incoming else "⬅️"
        preview = (self.message_text[:50] + '...') if len(self.message_text) > 50 else self.message_text
        return f"{direction} {self.bot_user.first_name}: {preview}"


class ReminderSettings(models.Model):
    """
    Налаштування нагадувань для конкретного користувача та автомобіля
    """
    REMINDER_TYPES = [
        ('oil_change', 'Заміна оливи'),
        ('maintenance', 'Планове ТО'),
        ('part_arrival', 'Прибуття запчастини'),
        ('service_complete', 'Завершення ремонту'),
        ('inspection_due', 'Техогляд'),
        ('insurance_due', 'Страховка'),
        ('custom', 'Інше'),
    ]
    
    bot_user = models.ForeignKey(
        BotUser,
        on_delete=models.CASCADE,
        related_name='reminder_settings',
        verbose_name="Користувач"
    )
    truck = models.ForeignKey(
        'clients.Truck',
        on_delete=models.CASCADE,
        related_name='reminder_settings',
        null=True,
        blank=True,
        verbose_name="Автомобіль"
    )
    
    reminder_type = models.CharField(
        max_length=50,
        choices=REMINDER_TYPES,
        verbose_name="Тип нагадування"
    )
    
    # Налаштування
    is_enabled = models.BooleanField(
        default=True,
        verbose_name="Увімкнено"
    )
    advance_days = models.IntegerField(
        default=3,
        verbose_name="За скільки днів нагадувати"
    )
    advance_km = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="За скільки км нагадувати"
    )
    
    # Розклад сповіщень
    notify_time = models.TimeField(
        default='09:00',
        verbose_name="Час сповіщення"
    )
    repeat_days = models.IntegerField(
        default=1,
        verbose_name="Повторювати кожні N днів"
    )
    
    class Meta:
        verbose_name = "Налаштування нагадування"
        verbose_name_plural = "Налаштування нагадувань"
        unique_together = ['bot_user', 'truck', 'reminder_type']

    def __str__(self):
        truck_info = f" - {self.truck.license_plate}" if self.truck else ""
        return f"{self.bot_user.get_full_name()}: {self.get_reminder_type_display()}{truck_info}"


class SentReminder(models.Model):
    """
    Історія відправлених нагадувань
    """
    bot_user = models.ForeignKey(
        BotUser,
        on_delete=models.CASCADE,
        related_name='sent_reminders',
        verbose_name="Користувач"
    )
    truck = models.ForeignKey(
        'clients.Truck',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Автомобіль"
    )
    
    reminder_type = models.CharField(
        max_length=50,
        verbose_name="Тип нагадування"
    )
    message_text = models.TextField(
        verbose_name="Текст повідомлення"
    )
    
    # Статус доставки
    is_delivered = models.BooleanField(
        default=False,
        verbose_name="Доставлено"
    )
    delivery_error = models.TextField(
        blank=True,
        verbose_name="Помилка доставки"
    )
    
    # Реакція користувача
    is_read = models.BooleanField(
        default=False,
        verbose_name="Прочитано"
    )
    user_action = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Дія користувача"
    )
    
    sent_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Відправлено"
    )

    class Meta:
        verbose_name = "Відправлене нагадування"
        verbose_name_plural = "Відправлені нагадування"
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.bot_user.get_full_name()} - {self.reminder_type} - {self.sent_at}"


class BotCommand(models.Model):
    """
    Команди бота та статистика їх використання
    """
    command = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Команда"
    )
    description = models.CharField(
        max_length=255,
        verbose_name="Опис"
    )
    required_role = models.CharField(
        max_length=20,
        choices=BotUser.ROLE_CHOICES,
        default='guest',
        verbose_name="Мінімальна роль"
    )
    
    # Статистика
    usage_count = models.IntegerField(
        default=0,
        verbose_name="Кількість використань"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна"
    )
    last_used = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Остання використана"
    )

    class Meta:
        verbose_name = "Команда бота"
        verbose_name_plural = "Команди бота"
        ordering = ['-usage_count']

    def __str__(self):
        return f"/{self.command} - {self.description}"

    def increment_usage(self):
        """Збільшує лічильник використань"""
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])