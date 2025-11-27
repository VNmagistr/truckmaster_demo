# maintenance/admin.py

from django.contrib import admin
from .models import FluidChangeRecord, ServiceReminder, TruckFluidSpec


@admin.register(FluidChangeRecord)
class FluidChangeRecordAdmin(admin.ModelAdmin):
    list_display = [
        'truck', 
        'subcategory', 
        'product', 
        'quantity', 
        'mileage', 
        'next_change_mileage',
        'performed_at'
    ]
    list_filter = ['subcategory', 'performed_at', 'created_by']
    search_fields = [
        'truck__license_plate', 
        'truck__last_seven_vin',
        'product__name',
        'notes'
    ]
    date_hierarchy = 'performed_at'
    readonly_fields = ['created_at', 'total_price']
    
    fieldsets = (
        ('Вантажівка', {
            'fields': ('truck', 'service_order')
        }),
        ('Заміна', {
            'fields': ('subcategory', 'product', 'quantity', 'mileage')
        }),
        ('Наступна заміна', {
            'fields': ('next_change_mileage', 'next_change_date')
        }),
        ('Вартість', {
            'fields': ('unit_price', 'total_price')
        }),
        ('Додатково', {
            'fields': ('notes', 'performed_at', 'created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ServiceReminder)
class ServiceReminderAdmin(admin.ModelAdmin):
    list_display = [
        'truck', 
        'title', 
        'subcategory',
        'status', 
        'priority', 
        'target_date', 
        'target_mileage'
    ]
    list_filter = ['status', 'priority', 'subcategory', 'reminder_type']
    search_fields = ['truck__license_plate', 'title', 'description']
    list_editable = ['status', 'priority']
    date_hierarchy = 'target_date'
    
    fieldsets = (
        ('Вантажівка', {
            'fields': ('truck',)
        }),
        ('Нагадування', {
            'fields': ('title', 'description', 'subcategory')
        }),
        ('Параметри', {
            'fields': ('reminder_type', 'target_mileage', 'target_date', 'priority')
        }),
        ('Статус', {
            'fields': ('status', 'completed_order', 'completed_at')
        }),
    )
    
    actions = ['mark_as_completed', 'mark_as_dismissed']
    
    @admin.action(description='Позначити як виконано')
    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='completed', completed_at=timezone.now())
    
    @admin.action(description='Відхилити')
    def mark_as_dismissed(self, request, queryset):
        queryset.update(status='dismissed')


@admin.register(TruckFluidSpec)
class TruckFluidSpecAdmin(admin.ModelAdmin):
    list_display = [
        'truck', 
        'subcategory', 
        'recommended_product', 
        'fill_volume',
        'change_interval_km'
    ]
    list_filter = ['subcategory']
    search_fields = [
        'truck__license_plate', 
        'truck__last_seven_vin',
        'recommended_product__name'
    ]
    filter_horizontal = ['alternative_products']
    
    fieldsets = (
        ('Вантажівка', {
            'fields': ('truck', 'subcategory')
        }),
        ('Рекомендації', {
            'fields': ('recommended_product', 'alternative_products', 'fill_volume')
        }),
        ('Інтервали', {
            'fields': ('change_interval_km', 'change_interval_months')
        }),
        ('Примітки', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )