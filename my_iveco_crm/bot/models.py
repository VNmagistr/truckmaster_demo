from django.db import models
from clients.models import Client, Truck

class BotUser(models.Model):
    ROLE_CHOICES = [
        ('guest',  'Гість'),
        ('driver', 'Водій'),
        ('owner',  'Власник'),
        ('admin',  'Адміністратор'),
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

    def get_full_name(self):
        parts = [self.first_name, self.last_name]
        return ' '.join(p for p in parts if p) or str(self.telegram_id)

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


class MileageReport(models.Model):
    """Пробіг вантажівки, введений власником через бот."""
    bot_user = models.ForeignKey(BotUser, on_delete=models.CASCADE, verbose_name="Користувач")
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, verbose_name="Вантажівка", related_name='mileage_reports')
    mileage = models.PositiveIntegerField(verbose_name="Пробіг (км)")
    reported_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата введення")

    class Meta:
        verbose_name = "Звіт про пробіг"
        verbose_name_plural = "Звіти про пробіг"
        ordering = ['-reported_at']

    def __str__(self):
        return f"{self.truck.license_plate} — {self.mileage} км ({self.reported_at.strftime('%d.%m.%Y')})"


class BotSettings(models.Model):
    """Глобальні налаштування бота. Завжди існує рівно один запис."""
    ask_mileage_enabled = models.BooleanField(
        default=False,
        verbose_name="Щотижневий запит пробігу",
        help_text="Щопонеділка о 10:00 власникам надсилається запит на введення поточного пробігу."
    )

    class Meta:
        verbose_name = "Налаштування бота"
        verbose_name_plural = "Налаштування бота"

    def __str__(self):
        return "Налаштування бота"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


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


class UnknownPlateSearch(models.Model):
    """Номерні знаки, яких не знайдено при пошуку через бот."""
    plate = models.CharField(max_length=32, unique=True, verbose_name="Номерний знак")
    search_count = models.PositiveIntegerField(default=1, verbose_name="К-ть пошуків")
    first_searched_at = models.DateTimeField(auto_now_add=True, verbose_name="Перший пошук")
    last_searched_at = models.DateTimeField(auto_now=True, verbose_name="Останній пошук")
    last_searched_by = models.ForeignKey(
        BotUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='unknown_plate_searches', verbose_name="Хто шукав останнім"
    )
    notes = models.CharField(max_length=255, blank=True, verbose_name="Нотатка")

    class Meta:
        verbose_name = "Невідомий номер"
        verbose_name_plural = "Невідомі номери"
        ordering = ['-last_searched_at']

    def __str__(self):
        return f"{self.plate} (×{self.search_count})"