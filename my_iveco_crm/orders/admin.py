from django.contrib import admin
from .models import (
    Employee, WorkGroup, ServiceOrder, ServiceWork, 
    RepairPhoto, MaintenanceRule, MaintenanceLog, WorkPrice, MaintenanceKit,
    FilterType, MaintenanceKitFilter
)
from inventory.models import UsedPart 

# Вбудовані адмінки для зручного редагування
class UsedPartInline(admin.TabularInline):
    model = UsedPart
    autocomplete_fields = ['part']
    extra = 1

class ServiceWorkInline(admin.TabularInline):
    model = ServiceWork
    autocomplete_fields = ['work', 'employee'] 
    extra = 1
    fields = ('work', 'employee', 'hours_spent', 'description')

class RepairPhotoInline(admin.TabularInline):
    model = RepairPhoto
    extra = 1

# Головна адмінка для Замовлення-наряду
@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'client', 'truck', 'status', 'total_cost', 'created_at')
    list_filter = ('status', 'created_at', 'client')
    search_fields = ('order_number', 'client__name', 'truck__license_plate')
    autocomplete_fields = ('client', 'truck')
    readonly_fields = ('total_cost', 'get_all_parts_display')

    fieldsets = (
        ('Основна інформація', {
            'fields': ('order_number', 'client', 'truck', 'status')
        }),
        ('Опис проблеми (від клієнта)', {
            'classes': ('collapse',), 
            'fields': ('problem_description',)
        }),
        ('Вартість', {
            'fields': ('total_cost',)
        }),
        ('Використані запчастини', {
            'fields': ('get_all_parts_display',),
            'description': 'Автоматично підтягуються з виконаних робіт'
        }),
    )

    inlines = [ServiceWorkInline, RepairPhotoInline]

    def get_all_parts_display(self, obj):
        """Показує всі запчастини по всіх роботах замовлення"""
        from django.utils.html import format_html
        from inventory.models import UsedPart
    
        if not obj.pk:
            return "Спочатку збережіть замовлення"
    
        parts = UsedPart.objects.filter(
            service_work__service_order=obj
        ).select_related('part', 'service_work__work')
    
        if not parts:
            return "Запчастини не додано"
    
        rows = []
        for p in parts:
            work_name = p.service_work.work.name if p.service_work.work else "—"
        
            # Визначаємо одиницю виміру: літри для оливи (рідини), штуки для решти
            part_name_lower = p.part.name.lower()

            # Спочатку перевіряємо чи це НЕ фільтр
            is_filter = 'фільтр' in part_name_lower or 'filter' in part_name_lower
            is_oil_liquid = ('олив' in part_name_lower or 'масло' in part_name_lower or 'oil' in part_name_lower)

            # Літри тільки якщо це олива (рідина), а НЕ фільтр
            if is_oil_liquid and not is_filter:
                quantity_display = f"{p.quantity} л"
            else:
                quantity_display = f"{p.quantity} шт."
        
            rows.append(
                f"<tr>"
                f"<td style='padding: 5px; border-bottom: 1px solid #ddd;'>{p.part.sku_code}</td>"
                f"<td style='padding: 5px; border-bottom: 1px solid #ddd;'>{p.part.name}</td>"
                f"<td style='padding: 5px; border-bottom: 1px solid #ddd; text-align: center;'>{quantity_display}</td>"
                f"<td style='padding: 5px; border-bottom: 1px solid #ddd;'>{work_name}</td>"
                f"</tr>"
            )
    
        table = f"""
        <table style='width: 100%; border-collapse: collapse;'>
            <thead>
                <tr style='background: #f0f0f0;'>
                    <th style='padding: 8px; text-align: left;'>Артикул</th>
                    <th style='padding: 8px; text-align: left;'>Запчастина</th>
                    <th style='padding: 8px; text-align: center;'>Кількість</th>
                    <th style='padding: 8px; text-align: left;'>До роботи</th>
                </tr>
            </thead>
            <tbody>
            {''.join(rows)}
            </tbody>
        </table>
        """
        return format_html(table)

    get_all_parts_display.short_description = 'Перелік запчастин'

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        if formset.model == ServiceWork and form.instance.pk:
            form.instance.update_total_cost()

# Решта адмін-панелей
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'position')
    search_fields = ('name',) 
    ordering = ['name'] 

@admin.register(WorkGroup)
class WorkGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'hourly_rate')
    search_fields = ('name',) 
    ordering = ['name']

@admin.register(ServiceWork)
class ServiceWorkAdmin(admin.ModelAdmin):
    list_display = ('service_order', 'work', 'employee', 'hours_spent')
    autocomplete_fields = ('service_order', 'work', 'employee')
    inlines = [UsedPartInline]
    search_fields = ['description', 'service_order__order_number', 'work__name']
    ordering = ['-service_order'] 

@admin.register(MaintenanceRule)
class MaintenanceRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'km_interval', 'description')
    search_fields = ('name',)
    filter_horizontal = ('applicable_models',)
    ordering = ['name'] 

@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ('truck', 'rule', 'date_performed')
    autocomplete_fields = ('truck', 'rule')
    ordering = ['-date_performed'] 

@admin.register(WorkPrice)
class WorkPriceAdmin(admin.ModelAdmin):
    list_display = ('name', 'work_group', 'standard_hours', 'get_calculated_price')
    list_filter = ('work_group',)
    search_fields = ('name',) 
    autocomplete_fields = ['work_group']
    ordering = ['name']
    
    def get_calculated_price(self, obj):
        """Показує розраховану ціну"""
        return f"{obj.get_calculated_price():.2f} грн"
    get_calculated_price.short_description = 'Розрахункова ціна'

# Inline для фільтрів у комплекті ТО
class MaintenanceKitFilterInline(admin.TabularInline):
    model = MaintenanceKitFilter
    extra = 1
    autocomplete_fields = ['filter_type', 'part']
    fields = ('filter_type', 'part', 'quantity', 'custom_interval_km', 'notes')

@admin.register(MaintenanceKit)
class MaintenanceKitAdmin(admin.ModelAdmin):
    list_display = ('get_vin', 'get_license_plate', 'oil', 'oil_quantity', 'oil_replacement_interval', 'updated_at')
    search_fields = ('truck__last_seven_vin', 'truck__full_vin', 'truck__license_plate')
    autocomplete_fields = ['truck', 'oil']
    
    inlines = [MaintenanceKitFilterInline]  # <-- Додали inline
    
    def get_vin(self, obj):
        return obj.truck.last_seven_vin
    get_vin.short_description = 'VIN (останні 7)'
    
    def get_license_plate(self, obj):
        return obj.truck.license_plate
    get_license_plate.short_description = 'Номер'
    
    fieldsets = (
        ('Автомобіль', {
            'fields': ('truck',)
        }),
        ('Олива', {
            'fields': ('oil', 'oil_quantity', 'oil_replacement_interval')
        }),
        ('Додатково', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

@admin.register(FilterType)
class FilterTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'euro_standard', 'get_models', 'replacement_interval_km')
    list_filter = ('euro_standard', 'applicable_models')
    search_fields = ('name', 'description')
    filter_horizontal = ('applicable_models',)
    ordering = ['name', 'euro_standard']
    
    def get_models(self, obj):
        """Показує для яких моделей підходить"""
        if not obj.applicable_models.exists():
            return "Всі моделі"
        return ", ".join([m.name for m in obj.applicable_models.all()[:3]])
    get_models.short_description = 'Моделі'
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('name', 'description')
        }),
        ('Застосовність', {
            'fields': ('applicable_models', 'euro_standard'),
            'description': 'Вкажіть для яких моделей та євростандартів підходить цей фільтр'
        }),
        ('Обслуговування', {
            'fields': ('replacement_interval_km',)
        }),
    )