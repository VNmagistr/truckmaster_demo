# maintenance/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from dateutil.relativedelta import relativedelta


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
    related_subcategories = models.ManyToManyField(
        'inventory.ProductSubcategory',
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
        4. НОВИЙ: Створення нагадування про наступну заміну
        """
        
        is_new = self.pk is None  # ← ВАЖЛИВО: перевіряємо ДО save()
        
        # 1. Розрахунок наступної заміни за пробігом
        if self.mileage and not self.next_change_mileage:
            if self.subcategory and self.subcategory.default_change_interval_km:
                interval_km = self.subcategory.default_change_interval_km
                self.next_change_mileage = self.mileage + interval_km
        
        # 2. Розрахунок наступної заміни за датою
        if not self.next_change_date:
            if self.performed_at:
                performed_date = self.performed_at.date() if hasattr(self.performed_at, 'date') else self.performed_at
                self.next_change_date = performed_date + relativedelta(years=1)
        
        # 3. Розрахунок загальної вартості
        if self.quantity and self.unit_price:
            self.total_price = self.quantity * self.unit_price
        
        super().save(*args, **kwargs)
        
        # 4. Автоматичне створення нагадування (тільки для нових записів)
        if is_new:  # ← ВАЖЛИВО: викликаємо ПІСЛЯ save()
            self._create_reminder()
    
def _create_reminder(self):
    	"""
        Автоматично створює нагадування про наступну заміну
        на основі типу обслуговування пов'язаного з підкатегорією
        """
        # Шукаємо тип обслуговування для цієї підкатегорії
        service_types = ServiceType.objects.filter(
            related_subcategories=self.subcategory,
            is_active=True
        )
        
        for service_type in service_types:
            # Перевіряємо чи не існує вже активне нагадування
            existing = ServiceReminder.objects.filter(
                truck=self.truck,
                service_type=service_type,
                status__in=['pending', 'notified']
            ).exists()
            
            if not existing:
                # Створюємо нагадування
                ServiceReminder.objects.create(
                    truck=self.truck,
                    service_type=service_type,
                    title=f"{service_type.name} для {self.truck.license_plate}",
                    description=f"Автоматично створено на основі заміни {self.subcategory.name}",
                    reminder_type='both',
                    target_mileage=self.next_change_mileage,
                    target_date=self.next_change_date,
                    priority=service_type.default_priority
                )


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
    
    # ЗМІНЕНО: замість subcategory використовуємо service_type
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
