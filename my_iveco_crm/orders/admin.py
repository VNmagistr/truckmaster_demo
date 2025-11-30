from inventory.models import UsedPart
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from .models import (
    Employee, WorkGroup, ServiceOrder, ServiceWork, 
    RepairPhoto, MaintenanceRule, MaintenanceLog, WorkPrice, MaintenanceKit,
    FilterType, MaintenanceKitFilter
)

# Вбудовані адмінки для зручного редагування
class UsedPartInline(admin.TabularInline):
    model = UsedPart  # ← НЕ строка!
    autocomplete_fields = ['part', 'warehouse']
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

    inlines = [ServiceWorkInline, RepairPhotoInline]  # ← ДОДАТИ

    class Media:  # ← ДОДАТИ
        js = ('js/admin/filter_trucks_by_client.js',)

    def get_urls(self):  # ← ДОДАТИ
        urls = super().get_urls()
        custom_urls = [
            path('get-trucks-by-client/', self.admin_site.admin_view(self.get_trucks_by_client), name='get_trucks_by_client'),
        ]
        return custom_urls + urls

    def get_trucks_by_client(self, request):  # ← ДОДАТИ
        """API endpoint для отримання вантажівок по клієнту"""
        from clients.models import Truck
        
        client_id = request.GET.get('client_id')
        
        if not client_id:
            return JsonResponse({'trucks': []})
        
        trucks = Truck.objects.filter(client_id=client_id).values(
            'id', 'license_plate', 'specific_model_name', 'last_seven_vin'
        )
        
        trucks_list = [
            {
                'id': t['id'],
                'text': f"{t['specific_model_name']} ({t['license_plate']}) - VIN: ...{t['last_seven_vin']}"
            }
            for t in trucks
        ]
        
        return JsonResponse({'trucks': trucks_list})

    def get_all_parts_display(self, obj):  # ← ДОДАТИ ЦЕЙ МЕТОД!
        """Показує всі запчастини"""
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
            
            part_name_lower = p.part.name.lower()
            is_filter = 'фільтр' in part_name_lower or 'filter' in part_name_lower
            is_oil_liquid = ('олив' in part_name_lower or 'масло' in part_name_lower or 'oil' in part_name_lower)
            
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

    def save_formset(self, request, form, formset, change):  # ← ДОДАТИ
        super().save_formset(request, form, formset, change)
        if formset.model == ServiceWork and form.instance.pk:
            form.instance.update_total_cost()


# Решта адмін-панелей
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'position')
    search_fields = ('name',)  # ← Обов'язково для autocomplete!
    ordering = ['name'] 

@admin.register(WorkGroup)
class WorkGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'hourly_rate')
    search_fields = ('name',)  # ← Обов'язково для autocomplete!
    ordering = ['name']

@admin.register(WorkPrice)
class WorkPriceAdmin(admin.ModelAdmin):
    list_display = ('name', 'work_group', 'standard_hours', 'get_calculated_price')
    list_filter = ('work_group',)
    search_fields = ('name',)  # ← Обов'язково для autocomplete!
    autocomplete_fields = ['work_group']
    ordering = ['name']
    
    def get_calculated_price(self, obj):
        """Показує розраховану ціну"""
        return f"{obj.get_calculated_price():.2f} грн"
    get_calculated_price.short_description = 'Розрахункова ціна'

@admin.register(ServiceWork)
class ServiceWorkAdmin(admin.ModelAdmin):
    list_display = ('service_order', 'work', 'employee', 'hours_spent')
    autocomplete_fields = ('service_order', 'work', 'employee')
    inlines = [UsedPartInline]  # ← ТІЛЬКИ це!
    search_fields = ['description', 'service_order__order_number', 'work__name']
    ordering = ['-service_order']