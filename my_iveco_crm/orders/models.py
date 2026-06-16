import uuid
from django.db import models
from django.conf import settings
from core.models import SoftDeleteModel
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from django.core.exceptions import ValidationError

MAX_REPAIR_PHOTOS_PER_ORDER = 20

# Імпортуємо тільки існуючі моделі
from clients.models import Client, Truck, IvecoBaseModel
from inventory.models import UsedPart, Product


def validate_image(file):
    max_size_mb = 10
    allowed_extensions = ['jpg', 'jpeg', 'png', 'webp']
    ext = file.name.rsplit('.', 1)[-1].lower() if '.' in file.name else ''
    if ext not in allowed_extensions:
        raise ValidationError(f'Дозволені формати: {", ".join(allowed_extensions)}')
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f'Максимальний розмір файлу — {max_size_mb} МБ')


def get_repair_photo_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    return f'repair_photos/{instance.service_order_id}/{uuid.uuid4().hex}.{ext}'


class ServiceOrderManager(models.Manager):
    def active(self):
        return self.filter(status__in=['OPEN', 'IN_PROGRESS'])
    
    def for_client(self, client):
        return self.filter(client=client).select_related('truck', 'client')
    
    def for_truck(self, truck):
        return self.filter(truck=truck).select_related('client')


class WorkGroup(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва категорії робіт")
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    
    class Meta:
        verbose_name = "Група робіт"
        verbose_name_plural = "Групи робіт"
    
    def __str__(self): 
        return self.name


class WorkPrice(models.Model):
    work_group = models.ForeignKey(WorkGroup, on_delete=models.CASCADE, related_name='works')
    name = models.CharField(max_length=255, verbose_name="Назва роботи")
    standard_hours = models.DecimalField(max_digits=5, decimal_places=2, default=1)

    class Meta:
        verbose_name = "Робота"
        verbose_name_plural = "Роботи"

    def __str__(self): 
        return self.name
    
    @property
    def price(self):
        return self.standard_hours * self.work_group.hourly_rate
    
    def get_calculated_price(self):
        return self.price


class ServiceOrder(SoftDeleteModel):
    class StatusChoices(models.TextChoices):
        OPEN = 'OPEN', 'Відкрито'
        IN_PROGRESS = 'IN_PROGRESS', 'В роботі'
        DONE = 'DONE', 'Виконано'
        CLOSED = 'CLOSED', 'Закрито'
        CANCELED = 'CANCELED', 'Скасовано'

    order_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, verbose_name="Клієнт")
    truck = models.ForeignKey(Truck, on_delete=models.PROTECT, verbose_name="Вантажівка")
    current_mileage = models.PositiveIntegerField(null=True, blank=True, verbose_name="Поточний пробіг")
    engine_hours = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Мотогодини",
        help_text="Заповнюється для моделей зі спецтехнікою (напр. Trakker)",
    )
    problem_description = models.TextField(blank=True, verbose_name="Опис проблеми")
    recommendations = models.TextField(blank=True, verbose_name="Рекомендації")
    car_photo = models.ImageField(upload_to='order_photos/cars/', blank=True, null=True, validators=[validate_image])
    odometer_photo = models.ImageField(upload_to='order_photos/odometers/', blank=True, null=True, validators=[validate_image])
    dashboard_photo = models.ImageField(upload_to='order_photos/dashboards/', blank=True, null=True, validators=[validate_image])
    
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.OPEN, verbose_name="Статус")
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Загальна вартість")
    intervals_snapshot = models.JSONField(null=True, blank=True, editable=False, verbose_name="Знімок інтервалів до DONE")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Створено")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Закрито")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Оновлено")


    objects = ServiceOrderManager()

    class Meta:
        verbose_name = "Наряд-замовлення"
        verbose_name_plural = "Наряди-замовлення"
        ordering = ['-created_at']

    def __str__(self): 
        return f"№{self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            from django.db.models import Max
            today = timezone.now().strftime('%Y%m%d')
            prefix = f"SO-{today}-"
            last_number = (
                ServiceOrder.objects.filter(order_number__startswith=prefix)
                .aggregate(max_num=Max('order_number'))['max_num']
            )
            if last_number:
                try:
                    seq = int(last_number.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1
            self.order_number = f"{prefix}{seq:04d}"
        super().save(*args, **kwargs)

    def update_total_cost(self):
        works_cost = self.works.aggregate(
            total=Sum(ExpressionWrapper(F('price_at_moment') * F('hours_spent'), output_field=DecimalField()))
        )['total'] or 0
        # Запчастини через ServiceWork
        work_parts_cost = UsedPart.objects.filter(
            service_work__service_order=self
        ).aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or 0
        # Запчастини додані напряму до замовлення
        direct_parts_cost = UsedPart.objects.filter(
            service_order=self, service_work__isnull=True
        ).aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or 0
        self.total_cost = works_cost + work_parts_cost + direct_parts_cost
        self.save(update_fields=['total_cost'])


class ServiceWork(models.Model):
    service_order = models.ForeignKey(
        ServiceOrder, 
        on_delete=models.CASCADE, 
        related_name="works",
        verbose_name="Наряд-замовлення"
    )
    work = models.ForeignKey(
        WorkPrice,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Робота"
    )
    custom_name = models.CharField(
        max_length=255, blank=True,
        verbose_name="Назва роботи в наряді"
    )
    description = models.TextField(blank=True, verbose_name="Опис")
    mechanic = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Механік"
    )
    hours_spent = models.DecimalField(max_digits=5, decimal_places=2, default=1, verbose_name="Витрачено годин")
    price_at_moment = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ціна")

    class Meta:
        verbose_name = "Виконана робота"
        verbose_name_plural = "Виконані роботи"

    @property
    def amount(self):
        return self.price_at_moment * self.hours_spent

    @property
    def display_name(self):
        if self.custom_name:
            return self.custom_name
        if self.work_id and self.work:
            return self.work.name
        return self.description or ''

    def save(self, *args, **kwargs):
        if self.work_id:
            self.price_at_moment = self.work.work_group.hourly_rate
        super().save(*args, **kwargs)


class RepairPhoto(models.Model):
    service_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to=get_repair_photo_path, validators=[validate_image])
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Фото ремонту"
        verbose_name_plural = "Фото ремонтів"


class OrderStatusHistory(models.Model):
    """Хронологія змін статусу замовлення."""
    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name="Замовлення"
    )
    from_status = models.CharField(max_length=20, blank=True, verbose_name="З статусу")
    to_status = models.CharField(max_length=20, verbose_name="На статус")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Хто змінив"
    )
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Час зміни")
    comment = models.TextField(blank=True, verbose_name="Коментар")

    class Meta:
        verbose_name = "Зміна статусу"
        verbose_name_plural = "Зміни статусу"
        ordering = ['changed_at']

    def __str__(self):
        from_label = self.from_status or '—'
        return f"{self.order} | {from_label} → {self.to_status}"


class MaintenanceRule(models.Model):
    name = models.CharField(max_length=255, verbose_name="Назва")
    km_interval = models.PositiveIntegerField(verbose_name="Інтервал (км)")
    applicable_models = models.ManyToManyField(IvecoBaseModel, verbose_name="Застосовні моделі")
    work = models.ForeignKey(
        'WorkPrice',
        on_delete=models.PROTECT,
        related_name='maintenance_rules',
        verbose_name="Послуга з довідника",
    )

    class Meta:
        verbose_name = "Правило ТО"
        verbose_name_plural = "Правила ТО"

    def __str__(self):
        return self.name


class MaintenanceLog(models.Model):
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, verbose_name="Вантажівка")
    rule = models.ForeignKey(MaintenanceRule, on_delete=models.CASCADE, verbose_name="Правило")
    date_performed = models.DateField(verbose_name="Дата виконання")
    mileage = models.PositiveIntegerField(null=True, blank=True, verbose_name="Пробіг")

    class Meta:
        verbose_name = "Запис ТО"
        verbose_name_plural = "Записи ТО"


class BaseMaintenanceKit(models.Model):
    """Базовий шаблон комплекту ТО для лінійки Iveco + стандарт Євро.
    Використовується як шаблон при створенні комплекту для конкретного авто.
    """
    base_model = models.ForeignKey(
        IvecoBaseModel,
        on_delete=models.CASCADE,
        related_name='base_kits',
        verbose_name="Базова модель"
    )
    euro_standard = models.CharField(
        max_length=10,
        choices=[
            ('', 'Будь-який'),
            ('EURO3', 'Євро-3'),
            ('EURO4', 'Євро-4'),
            ('EURO5', 'Євро-5'),
            ('EURO6', 'Євро-6'),
        ],
        blank=True,
        default='',
        verbose_name="Стандарт Євро"
    )
    oil = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='base_oil_for_kits',
        verbose_name="Олива"
    )
    oil_quantity = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Кількість оливи")
    oil_change_interval_km = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Інтервал заміни оливи (км)"
    )

    class Meta:
        unique_together = [['base_model', 'euro_standard']]
        verbose_name = "Базовий комплект ТО"
        verbose_name_plural = "Базові комплекти ТО"

    def __str__(self):
        euro = dict(self._meta.get_field('euro_standard').choices).get(self.euro_standard, self.euro_standard)
        return f"{self.base_model} — {euro}" if self.euro_standard else str(self.base_model)


SERVICE_TYPE_CHOICES = [
    ('both', 'Повне і часткове ТО'),
    ('full', 'Тільки повне ТО'),
    ('partial', 'Тільки часткове ТО'),
    ('rear_axle', 'Заміна оливи заднього моста'),
    ('gearbox', 'Заміна оливи КПП'),
    ('auto_gearbox', 'Заміна оливи АКПП'),
    ('auto_gearbox_filter', 'Заміна фільтра АКПП'),
    ('belts', 'Заміна ремнів/роликів'),
    ('chains', 'Заміна ланцюгів'),
]


class BaseMaintenanceKitFilter(models.Model):
    """Фільтр у базовому шаблоні комплекту ТО."""
    base_kit = models.ForeignKey(
        BaseMaintenanceKit,
        on_delete=models.CASCADE,
        related_name='filters',
        verbose_name="Базовий комплект ТО"
    )
    part = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        verbose_name="Запчастина"
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="Кількість")
    change_interval_km = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Інтервал заміни (км)"
    )
    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPE_CHOICES,
        default='both',
        verbose_name="Вид ТО",
        help_text="В якому виді ТО використовується цей фільтр"
    )

    class Meta:
        verbose_name = "Фільтр базового комплекту ТО"
        verbose_name_plural = "Фільтри базових комплектів ТО"


class MaintenanceKit(models.Model):
    truck = models.OneToOneField(
        Truck, 
        on_delete=models.CASCADE,
        verbose_name="Вантажівка"
    )
    # Використовуємо Product замість Part
    oil = models.ForeignKey(
        'inventory.Product', 
        on_delete=models.PROTECT, 
        related_name='oil_for_trucks',
        verbose_name="Олива"
    )
    oil_quantity = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Кількість оливи")
    oil_change_interval_km = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Інтервал заміни оливи (км)",
        help_text="Наприклад: 20000"
    )
    rear_axle_oil = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='rear_axle_oil_for_trucks',
        null=True, blank=True,
        verbose_name="Олива заднього моста"
    )
    rear_axle_oil_quantity = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name="Кількість оливи заднього моста"
    )
    gearbox_oil = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='gearbox_oil_for_trucks',
        null=True, blank=True,
        verbose_name="Олива КПП"
    )
    gearbox_oil_quantity = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name="Кількість оливи КПП"
    )
    auto_gearbox_oil = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='auto_gearbox_oil_for_trucks',
        null=True, blank=True,
        verbose_name="Олива АКПП"
    )
    auto_gearbox_oil_quantity = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name="Кількість оливи АКПП"
    )
    auto_gearbox_filter = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='auto_gearbox_filter_for_trucks',
        null=True, blank=True,
        verbose_name="Фільтр АКПП"
    )
    auto_gearbox_filter_quantity = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Кількість фільтрів АКПП"
    )

    def __str__(self):
        return f"Комплект ТО — {self.truck.specific_model_name} ({self.truck.license_plate})"

    class Meta:
        verbose_name = "Комплект ТО"
        verbose_name_plural = "Комплекти ТО"


class MaintenanceKitFilter(models.Model):
    maintenance_kit = models.ForeignKey(
        MaintenanceKit,
        on_delete=models.CASCADE,
        related_name='filters',
        verbose_name="Комплект ТО"
    )
    part = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        verbose_name="Запчастина"
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="Кількість")
    change_interval_km = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Інтервал заміни (км)",
        help_text="Наприклад: 20000"
    )
    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPE_CHOICES,
        default='both',
        verbose_name="Вид ТО",
        help_text="В якому виді ТО використовується цей фільтр"
    )

    class Meta:
        verbose_name = "Фільтр комплекту ТО"
        verbose_name_plural = "Фільтри комплектів ТО"


class TruckMaintenanceIntervals(models.Model):
    """Інтервали регламентних робіт для вантажівки."""

    class TrackingMode(models.TextChoices):
        MILEAGE = 'mileage', 'По кілометражу'
        ENGINE_HOURS = 'engine_hours', 'По мотогодинах'

    truck = models.OneToOneField(
        Truck,
        on_delete=models.CASCADE,
        related_name='maintenance_intervals',
        verbose_name="Вантажівка"
    )
    tracking_mode = models.CharField(
        max_length=20,
        choices=TrackingMode.choices,
        default=TrackingMode.MILEAGE,
        verbose_name="Режим обліку",
        help_text="Для спецтехніки (Trakker) можна вести облік у мотогодинах. "
                  "У режимі engine_hours поля *_interval/*_last_km інтерпретуються як години.",
    )
    engine_oil_interval = models.PositiveIntegerField(null=True, blank=True, verbose_name="Інтервал заміни оливи двигуна (км)")
    engine_oil_last_km   = models.PositiveIntegerField(null=True, blank=True, verbose_name="Пробіг при останній заміні оливи двигуна")
    gearbox_oil_interval = models.PositiveIntegerField(null=True, blank=True, verbose_name="Інтервал заміни оливи КПП (км)")
    gearbox_oil_last_km  = models.PositiveIntegerField(null=True, blank=True, verbose_name="Пробіг при останній заміні оливи КПП")
    auto_gearbox_oil_interval = models.PositiveIntegerField(null=True, blank=True, verbose_name="Інтервал заміни оливи АКПП (км)")
    auto_gearbox_oil_last_km  = models.PositiveIntegerField(null=True, blank=True, verbose_name="Пробіг при останній заміні оливи АКПП")
    auto_gearbox_filter_interval = models.PositiveIntegerField(null=True, blank=True, verbose_name="Інтервал заміни фільтра АКПП (км)")
    auto_gearbox_filter_last_km  = models.PositiveIntegerField(null=True, blank=True, verbose_name="Пробіг при останній заміні фільтра АКПП")
    rear_axle_oil_interval = models.PositiveIntegerField(null=True, blank=True, verbose_name="Інтервал заміни оливи заднього моста (км)")
    rear_axle_oil_last_km  = models.PositiveIntegerField(null=True, blank=True, verbose_name="Пробіг при останній заміні оливи заднього моста")
    belts_interval = models.PositiveIntegerField(null=True, blank=True, verbose_name="Інтервал заміни ремнів/роликів (км)")
    belts_last_km  = models.PositiveIntegerField(null=True, blank=True, verbose_name="Пробіг при останній заміні ремнів/роликів")
    chains_interval = models.PositiveIntegerField(null=True, blank=True, verbose_name="Інтервал заміни ланцюгів (км)")
    chains_last_km  = models.PositiveIntegerField(null=True, blank=True, verbose_name="Пробіг при останній заміні ланцюгів")

    class Meta:
        verbose_name = "Інтервали ТО вантажівки"
        verbose_name_plural = "Інтервали ТО вантажівок"

    def __str__(self):
        return f"Інтервали ТО: {self.truck}"


class MaintenanceIntervalsTemplate(models.Model):
    """
    Еталон інтервалів регламентних робіт за комбінацією
    (базова модель, євростандарт, тип КПП). Після збереження
    вантажівки сигнал заповнює її TruckMaintenanceIntervals
    значеннями зі знайденого еталона (тільки порожні поля).
    """
    base_model = models.ForeignKey(
        'clients.IvecoBaseModel',
        on_delete=models.CASCADE,
        related_name='interval_templates',
        verbose_name="Базова модель",
    )
    euro_standard = models.CharField(
        max_length=10,
        choices=[('', 'Будь-який')] + Truck.EURO_STANDARD_CHOICES,
        blank=True, default='',
        verbose_name="Євростандарт",
        help_text="Залиште порожнім, щоб еталон підходив до будь-якого євростандарту",
    )
    transmission_type = models.CharField(
        max_length=10,
        choices=[('', 'Будь-який')] + Truck.TRANSMISSION_CHOICES,
        blank=True, default='',
        verbose_name="Тип КПП",
        help_text="Залиште порожнім, щоб еталон підходив до будь-якої КПП",
    )
    tracking_mode = models.CharField(
        max_length=20,
        choices=TruckMaintenanceIntervals.TrackingMode.choices,
        default=TruckMaintenanceIntervals.TrackingMode.MILEAGE,
        verbose_name="Режим обліку",
    )

    engine_oil_interval          = models.PositiveIntegerField(null=True, blank=True, verbose_name="Інтервал заміни оливи двигуна")
    gearbox_oil_interval         = models.PositiveIntegerField(null=True, blank=True, verbose_name="Інтервал заміни оливи КПП")
    auto_gearbox_oil_interval    = models.PositiveIntegerField(null=True, blank=True, verbose_name="Інтервал заміни оливи АКПП")
    auto_gearbox_filter_interval = models.PositiveIntegerField(null=True, blank=True, verbose_name="Інтервал заміни фільтра АКПП")
    rear_axle_oil_interval       = models.PositiveIntegerField(null=True, blank=True, verbose_name="Інтервал заміни оливи заднього моста")
    belts_interval               = models.PositiveIntegerField(null=True, blank=True, verbose_name="Інтервал заміни ремнів/роликів")
    chains_interval              = models.PositiveIntegerField(null=True, blank=True, verbose_name="Інтервал заміни ланцюгів")

    # --- Мастила (еталонні) ---
    oil = models.ForeignKey(
        'inventory.Product', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tpl_oil',
        verbose_name="Олива двигуна",
    )
    oil_quantity = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="Кількість оливи двигуна",
    )
    rear_axle_oil = models.ForeignKey(
        'inventory.Product', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tpl_rear_axle_oil',
        verbose_name="Олива заднього моста",
    )
    rear_axle_oil_quantity = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="Кількість оливи заднього моста",
    )
    gearbox_oil = models.ForeignKey(
        'inventory.Product', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tpl_gearbox_oil',
        verbose_name="Олива КПП",
    )
    gearbox_oil_quantity = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="Кількість оливи КПП",
    )
    auto_gearbox_oil = models.ForeignKey(
        'inventory.Product', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tpl_auto_gearbox_oil',
        verbose_name="Олива АКПП",
    )
    auto_gearbox_oil_quantity = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="Кількість оливи АКПП",
    )
    auto_gearbox_filter = models.ForeignKey(
        'inventory.Product', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tpl_auto_gearbox_filter',
        verbose_name="Фільтр АКПП",
    )
    auto_gearbox_filter_quantity = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Кількість фільтрів АКПП",
    )

    notes = models.CharField(max_length=255, blank=True, default='', verbose_name="Нотатка")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    INTERVAL_FIELDS = (
        'engine_oil_interval',
        'gearbox_oil_interval',
        'auto_gearbox_oil_interval',
        'auto_gearbox_filter_interval',
        'rear_axle_oil_interval',
        'belts_interval',
        'chains_interval',
    )

    OIL_FIELDS = (
        ('oil', 'oil_quantity'),
        ('rear_axle_oil', 'rear_axle_oil_quantity'),
        ('gearbox_oil', 'gearbox_oil_quantity'),
        ('auto_gearbox_oil', 'auto_gearbox_oil_quantity'),
    )

    class Meta:
        verbose_name = "Еталон регламенту ТО"
        verbose_name_plural = "Еталони регламенту ТО"
        constraints = [
            models.UniqueConstraint(
                fields=['base_model', 'euro_standard', 'transmission_type'],
                name='uniq_template_per_combo',
            ),
        ]
        ordering = ['base_model__name', 'euro_standard', 'transmission_type']

    def __str__(self):
        parts = [self.base_model.name]
        if self.euro_standard:
            parts.append(self.get_euro_standard_display())
        if self.transmission_type:
            parts.append(self.get_transmission_type_display())
        return ' / '.join(parts)


class TemplateKitFilter(models.Model):
    """Фільтр/запчастина в еталонному комплекті ТО."""
    template = models.ForeignKey(
        MaintenanceIntervalsTemplate,
        on_delete=models.CASCADE,
        related_name='filters',
        verbose_name="Еталон ТО",
    )
    part = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        verbose_name="Запчастина",
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="Кількість")
    change_interval_km = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Інтервал заміни (км)",
    )
    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPE_CHOICES,
        default='both',
        verbose_name="Вид ТО",
        help_text="В якому виді ТО використовується цей фільтр",
    )

    class Meta:
        verbose_name = "Фільтр еталонного комплекту ТО"
        verbose_name_plural = "Фільтри еталонного комплекту ТО"

    def __str__(self):
        return f"{self.part} × {self.quantity}"
