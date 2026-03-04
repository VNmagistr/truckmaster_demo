# maintenance/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class ServiceType(models.Model):
    """
    Тип технічного обслуговування
    Приклади: Заміна моторної оливи, Заміна гальмівних колодок, Заміна ременя генератора
    """
    name = models.CharField('Назва', max_length=200)
    description = models.TextField('Опис', blank=True)
    
    # Інтервали обслуговування
    default_interval_km = models.PositiveIntegerField(
        'Інтервал за пробігом (км)',
        null=True, blank=True,
        help_text='Наприклад: 20000 км для моторної оливи'
    )
    default_interval_months = models.PositiveIntegerField(
        'Інтервал за часом (місяців)',
        null=True, blank=True,
        help_text='Наприклад: 12 місяців для моторної оливи'
    )
    
    # Пов'язані підкатегорії товарів (для автоматичного створення нагадувань)
    # ВИПРАВЛЕНО: SubCategory замість ProductSubcategory
    related_subcategories = models.ManyToManyField(
        'inventory.SubCategory',
        blank=True,
        verbose_name='Пов\'язані підкатегорії товарів',
        help_text='Коли змінюється товар з цієї підкатегорії - створюється нагадування цього типу'
    )
    
    # Пріоритет нагадування за замовчуванням
    default_priority = models.CharField(
        'Пріоритет за замовчуванням',
        max_length=20,
        choices=[
            ('low', 'Низький'),
            ('medium', 'Середній'),
            ('high', 'Високий'),
            ('critical', 'Критичний'),
        ],
        default='medium'
    )
    
    is_active = models.BooleanField('Активний', default=True)
    sort_order = models.IntegerField('Порядок сортування', default=0)

    class Meta:
        verbose_name = 'Тип технічного обслуговування'
        verbose_name_plural = 'Типи технічного обслуговування'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class ServiceReminder(models.Model):
    """
    Нагадування про планове обслуговування
    """
    REMINDER_TYPES = [
        ('mileage', 'За пробігом'),
        ('date', 'За датою'),
        ('both', 'За пробігом або датою'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Очікує'),
        ('notified', 'Сповіщено'),
        ('completed', 'Виконано'),
        ('overdue', 'Прострочено'),
        ('dismissed', 'Відхилено'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Низький'),
        ('medium', 'Середній'),
        ('high', 'Високий'),
        ('critical', 'Критичний'),
    ]

    truck = models.ForeignKey(
        'clients.Truck',
        on_delete=models.CASCADE,
        related_name='reminders',
        verbose_name='Вантажівка'
    )
    
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.PROTECT,
        verbose_name='Тип обслуговування',
        null=True,
        blank=True,
        help_text='Конкретний тип ТО (заміна оливи, колодок і т.д.)'
    )
    
    title = models.CharField('Назва', max_length=200)
    description = models.TextField('Опис', blank=True)
    
    reminder_type = models.CharField(
        'Тип нагадування',
        max_length=20,
        choices=REMINDER_TYPES,
        default='both'
    )
    target_mileage = models.PositiveIntegerField(
        'Цільовий пробіг (км)',
        null=True, blank=True
    )
    target_date = models.DateField(
        'Цільова дата',
        null=True, blank=True
    )
    NOTIFY_FREQUENCY_CHOICES = [
        (1,  'Щодня'),
        (2,  'Кожні 2 дні'),
        (3,  'Кожні 3 дні'),
        (7,  'Раз на тиждень'),
        (14, 'Раз на 2 тижні'),
    ]
    notify_frequency_days = models.PositiveSmallIntegerField(
        'Частота нагадувань',
        choices=NOTIFY_FREQUENCY_CHOICES,
        default=7,
        help_text='Як часто повторювати повідомлення власнику поки ТО не виконано.'
    )
    last_notified_at = models.DateTimeField(
        'Останнє надсилання',
        null=True, blank=True,
        editable=False,
    )

    interval_km = models.PositiveIntegerField(
        'Інтервал за пробігом (км)',
        null=True, blank=True,
        help_text='Через скільки км створювати наступне нагадування. Порожньо — з типу ТО.'
    )
    interval_months = models.PositiveIntegerField(
        'Інтервал за часом (місяців)',
        null=True, blank=True,
        help_text='Через скільки місяців створювати наступне нагадування. Порожньо — з типу ТО.'
    )
    
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    priority = models.CharField(
        'Пріоритет',
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    
    completed_order = models.ForeignKey(
        'orders.ServiceOrder',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Виконане замовлення'
    )
    completed_at = models.DateTimeField('Дата виконання', null=True, blank=True)
    
    created_at = models.DateTimeField('Створено', auto_now_add=True)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)

    class Meta:
        verbose_name = 'Нагадування про ТО'
        verbose_name_plural = 'Нагадування про ТО'
        ordering = ['status', 'target_date', 'target_mileage']

    def __str__(self):
        return f"{self.truck} - {self.title}"

    def check_status(self, current_mileage=None):
        """Перевірка та оновлення статусу"""
        if self.status in ['completed', 'dismissed']:
            return self.status
        
        today = timezone.now().date()
        is_overdue = False
        
        if self.target_date and today > self.target_date:
            is_overdue = True
        
        if current_mileage and self.target_mileage and current_mileage > self.target_mileage:
            is_overdue = True
        
        if is_overdue and self.status != 'overdue':
            self.status = 'overdue'
            self.save(update_fields=['status'])
        
        return self.status


