# maintenance/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from dateutil.relativedelta import relativedelta


class FluidChangeRecord(models.Model):
    """
    Запис про заміну рідини/оливи для конкретної вантажівки
    """
    truck = models.ForeignKey(
        'clients.Truck',
        on_delete=models.CASCADE,
        related_name='fluid_changes',
        verbose_name='Вантажівка'
    )
    subcategory = models.ForeignKey(
        'inventory.ProductSubcategory',
        on_delete=models.PROTECT,
        verbose_name='Тип рідини/оливи'
    )
    product = models.ForeignKey(
        'inventory.Part',
        on_delete=models.PROTECT,
        verbose_name='Використаний товар'
    )
    
    quantity = models.DecimalField(
        'Кількість (л/шт)',
        max_digits=8, decimal_places=2
    )
    mileage = models.PositiveIntegerField('Пробіг при заміні (км)')
    
    next_change_mileage = models.PositiveIntegerField(
        'Наступна заміна (км)',
        null=True, blank=True,
        help_text='Розраховується автоматично на основі інтервалу підкатегорії'
    )
    next_change_date = models.DateField(
        'Наступна заміна (дата)',
        null=True, blank=True,
        help_text='Розраховується автоматично: +1 рік від дати виконання'
    )
    
    service_order = models.ForeignKey(
        'orders.ServiceOrder',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fluid_changes',
        verbose_name='Наряд-замовлення'
    )
    
    unit_price = models.DecimalField(
        'Ціна за одиницю',
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    total_price = models.DecimalField(
        'Загальна вартість',
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    
    notes = models.TextField('Примітки', blank=True)
    performed_at = models.DateTimeField('Дата виконання', default=timezone.now)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Виконав'
    )
    created_at = models.DateTimeField('Створено', auto_now_add=True)

    class Meta:
        verbose_name = 'Запис про заміну рідини'
        verbose_name_plural = 'Історія замін рідин'
        ordering = ['-performed_at']

    def __str__(self):
        return f"{self.truck} - {self.subcategory.name} ({self.performed_at.date()})"

    def save(self, *args, **kwargs):
        """
        Автоматичний розрахунок:
        1. Наступної заміни за пробігом (якщо не вказано вручну)
        2. Наступної заміни за датою (якщо не вказано вручну)
        3. Загальної вартості
        """
        
        # 1. Розрахунок наступної заміни за пробігом
        if self.mileage and not self.next_change_mileage:
            # Беремо інтервал з підкатегорії
            if self.subcategory and self.subcategory.default_change_interval_km:
                interval_km = self.subcategory.default_change_interval_km
                self.next_change_mileage = self.mileage + interval_km
        
        # 2. Розрахунок наступної заміни за датою (якщо не вказано вручну)
        if not self.next_change_date:
            # Беремо дату виконання (performed_at) і додаємо 1 рік
            if self.performed_at:
                performed_date = self.performed_at.date() if hasattr(self.performed_at, 'date') else self.performed_at
                self.next_change_date = performed_date + relativedelta(years=1)
        
        # 3. Розрахунок загальної вартості
        if self.quantity and self.unit_price:
            self.total_price = self.quantity * self.unit_price
        
        super().save(*args, **kwargs)


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
    
    title = models.CharField('Назва', max_length=200)
    description = models.TextField('Опис', blank=True)
    subcategory = models.ForeignKey(
        'inventory.ProductSubcategory',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Тип обслуговування'
    )
    
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


class TruckFluidSpec(models.Model):
    """
    Рекомендовані рідини для конкретної вантажівки (по VIN)
    """
    truck = models.ForeignKey(
        'clients.Truck',
        on_delete=models.CASCADE,
        related_name='fluid_specs',
        verbose_name='Вантажівка'
    )
    subcategory = models.ForeignKey(
        'inventory.ProductSubcategory',
        on_delete=models.CASCADE,
        verbose_name='Тип рідини'
    )
    
    recommended_product = models.ForeignKey(
        'inventory.Part',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='recommended_for_trucks',
        verbose_name='Рекомендований товар'
    )
    alternative_products = models.ManyToManyField(
        'inventory.Part',
        blank=True,
        related_name='alternative_for_trucks',
        verbose_name='Альтернативні товари'
    )
    
    fill_volume = models.DecimalField(
        'Об\'єм заправки (л)',
        max_digits=6, decimal_places=2,
        null=True, blank=True
    )
    change_interval_km = models.PositiveIntegerField(
        'Інтервал заміни (км)',
        null=True, blank=True
    )
    change_interval_months = models.PositiveIntegerField(
        'Інтервал заміни (місяців)',
        null=True, blank=True
    )
    
    notes = models.TextField('Примітки', blank=True)
    
    class Meta:
        verbose_name = 'Специфікація рідин'
        verbose_name_plural = 'Специфікації рідин'
        unique_together = ['truck', 'subcategory']

    def __str__(self):
        return f"{self.truck} - {self.subcategory.name}"