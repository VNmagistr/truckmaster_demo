from django.contrib import admin
from .models import Employee, ServiceOrder, ServiceWork, MaintenanceRule, MaintenanceLog, WorkGroup


@admin.register(WorkGroup)
class WorkGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_per_hour')
    search_fields = ('name',)
    
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'position', 'phone')
    search_fields = ('name', 'position')

@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    # Видалили 'id' з list_display
    list_display = ('client', 'truck', 'status', 'start_date', 'end_date', 'total_cost') 
    list_filter = ('status', 'start_date')
    search_fields = ('client__name', 'truck__license_plate', 'description')
    date_hierarchy = 'start_date'

@admin.register(ServiceWork)
class ServiceWorkAdmin(admin.ModelAdmin):
    list_display = ('job_description', 'service_order', 'employee', 'labor_cost', 'duration_hours')
    list_filter = ('employee',)
    search_fields = ('job_description', 'service_order__id')

@admin.register(MaintenanceRule)
class MaintenanceRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'interval_km', 'applicable_transmission')
    list_filter = ('applicable_transmission',)
    filter_horizontal = ('applicable_models',)
    search_fields = ('name',)

@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ('truck', 'rule', 'completion_date', 'completion_mileage')
    list_filter = ('rule', 'completion_date')
    search_fields = ('truck__license_plate', 'rule__name')
    date_hierarchy = 'completion_date'