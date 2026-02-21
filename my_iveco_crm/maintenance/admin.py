# maintenance/admin.py

from django.contrib import admin
from .models import ServiceReminder, ServiceType


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'default_interval_km',
        'default_interval_months',
        'default_priority',
        'sort_order',
        'is_active'
    ]
    list_filter = ['is_active', 'default_priority']
    search_fields = ['name', 'description']
    filter_horizontal = ['related_subcategories']
    list_editable = ['is_active', 'sort_order']
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('name', 'description', 'is_active', 'sort_order')
        }),
        ('Інтервали обслуговування', {
            'fields': ('default_interval_km', 'default_interval_months')
        }),
        ('Пов\'язані товари', {
            'fields': ('related_subcategories',),
            'description': 'При заміні товарів з цих підкатегорій автоматично створюються нагадування'
        }),
        ('Налаштування нагадувань', {
            'fields': ('default_priority',)
        }),
    )


@admin.register(ServiceReminder)
class ServiceReminderAdmin(admin.ModelAdmin):
    list_display = [
        'truck', 
        'service_type',
        'title', 
        'status', 
        'priority', 
        'target_date', 
        'target_mileage'
    ]
    list_filter = ['status', 'priority', 'service_type', 'reminder_type']
    search_fields = ['truck__license_plate', 'title', 'description']
    list_editable = ['status', 'priority']
    date_hierarchy = 'target_date'
    
    # Autocomplete
    autocomplete_fields = ['truck', 'completed_order', 'service_type']
    
    fieldsets = (
        ('Вантажівка', {
            'fields': ('truck',)
        }),
        ('Нагадування', {
            'fields': ('service_type', 'title', 'description')
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


