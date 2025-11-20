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

class RepairPhotoInline(admin.TabularInline):
    model = RepairPhoto
    extra = 1

# Головна адмінка для Замовлення-наряду
@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'client', 'truck', 'status', 'total_cost', 'created_at') # Додали total_cost
    list_filter = ('status', 'created_at', 'client')
    search_fields = ('order_number', 'client__name', 'truck__license_plate')
    autocomplete_fields = ('client', 'truck')

    fieldsets = (
        ('Основна інформація', {
            'fields': ('order_number', 'client', 'truck', 'status')
        }),
        ('Опис проблеми (від клієнта)', {
            'classes': ('collapse',), 
            'fields': ('problem_description',)
        }),
    )

    inlines = [ServiceWorkInline, RepairPhotoInline]

    
    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)

        # Якщо ми зберегли ServiceWork, потрібно перерахувати загальну вартість
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