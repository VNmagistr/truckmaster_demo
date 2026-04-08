from django.db import models
from django.contrib.auth.models import User  # Стандартний Django User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """
    Профіль користувача з додатковими полями
    Прив'язується до стандартного User через OneToOne
    """
    ROLE_CHOICES = [
        ('admin', 'Адміністратор'),
        ('manager', 'Менеджер'),
        ('mechanic', 'Механік'),
        ('storekeeper', 'Комірник'),
        ('accountant', 'Бухгалтер'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Користувач'
    )
    role = models.CharField(
        'Роль',
        max_length=20,
        choices=ROLE_CHOICES,
        default='mechanic'
    )
    phone = models.CharField('Телефон', max_length=20, blank=True)
    position = models.CharField('Посада', max_length=100, blank=True)
    
    warehouses = models.ManyToManyField(
        'inventory.Warehouse',
        blank=True,
        related_name='staff',
        verbose_name='Доступні склади'
    )

    class Meta:
        verbose_name = 'Профіль користувача'
        verbose_name_plural = 'Профілі користувачів'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    @property
    def is_admin_role(self):
        return self.role == 'admin' or self.user.is_superuser

    @property
    def is_manager_role(self):
        return self.role in ['admin', 'manager'] or self.user.is_superuser

    @property
    def is_mechanic_role(self):
        return self.role == 'mechanic'

    @property
    def is_storekeeper_role(self):
        return self.role == 'storekeeper'

    @property
    def is_accountant_role(self):
        return self.role == 'accountant'

    def can_access_warehouse(self, warehouse):
        if self.is_admin_role or self.is_manager_role:
            return True
        return self.warehouses.filter(pk=warehouse.pk).exists()


# Автоматичне створення профілю
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'profile'):
        UserProfile.objects.create(user=instance)



class UserActionLog(models.Model):
    """Журнал дій користувачів"""
    ACTION_TYPES = [
        ('login', 'Вхід в систему'),
        ('logout', 'Вихід з системи'),
        ('create', 'Створення'),
        ('update', 'Оновлення'),
        ('delete', 'Видалення'),
        ('view', 'Перегляд'),
        ('export', 'Експорт'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='action_logs',
        verbose_name='Користувач'
    )
    action_type = models.CharField('Тип дії', max_length=20, choices=ACTION_TYPES)
    model_name = models.CharField('Модель', max_length=100, blank=True)
    object_id = models.IntegerField('ID об\'єкта', null=True, blank=True)
    object_repr = models.CharField('Представлення', max_length=255, blank=True)
    changes = models.JSONField('Зміни', null=True, blank=True)
    ip_address = models.GenericIPAddressField('IP', null=True, blank=True)
    user_agent = models.TextField('User Agent', blank=True)
    created_at = models.DateTimeField('Дата/час', auto_now_add=True)

    class Meta:
        verbose_name = 'Журнал дій'
        verbose_name_plural = 'Журнал дій'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.get_action_type_display()} - {self.created_at}"
