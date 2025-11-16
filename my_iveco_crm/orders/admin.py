from django.contrib import admin
from .models import (
    Employee, WorkGroup, ServiceOrder, ServiceWork, 
    RepairPhoto, MaintenanceRule, MaintenanceLog, WorkPrice
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

    # 👇 ВИПРАВЛЕННЯ ФАТАЛЬНОЇ ПОМИЛКИ: Обробляємо збереження inlines 👇
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
    list_display = ('name', 'work_group', 'price')
    list_filter = ('work_group',)
    search_fields = ('name',) 
    autocomplete_fields = ['work_group']
    ordering = ['name']