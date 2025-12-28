# orders/admin.py - ОНОВЛЕННЯ

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
    """Запчастини прив'язані до роботи"""
    model = UsedPart
    fk_name = 'service_work'  # Явно вказуємо зв'язок
    autocomplete_fields = ['part', 'warehouse']
    extra = 1
    verbose_name = "Запчастина до роботи"
    verbose_name_plural = "Запчастини до роботи"
    fields = ('part', 'quantity', 'warehouse', 'unit_price')
    readonly_fields = ('unit_price',)


class DirectUsedPartInline(admin.TabularInline):
    """Запчастини додані напряму до замовлення (без прив'язки до роботи)"""
    model = UsedPart
    fk_name = 'service_order'  # Явно вказуємо зв'язок
    autocomplete_fields = ['part', 'warehouse']
    extra = 1
    verbose_name = "Запчастина (пряме додавання)"
    verbose_name_plural = "Запчастини (пряме додавання)"
    fields = ('part', 'quantity', 'warehouse', 'unit_price')
    readonly_fields = ('unit_price',)


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
    readonly_fields = ('total_cost', 'get_all_parts_display', 'get_cost_breakdown')

    fieldsets = (
        ('Основна інформація', {
            'fields': ('order_number', 'client', 'truck', 'status')
        }),
        ('Опис проблеми (від клієнта)', {
            'classes': ('collapse',), 
            'fields': ('problem_description',)
        }),
        ('Вартість', {
            'fields': ('total_cost', 'get_cost_breakdown')
        }),
        ('Використані запчастини', {
            'fields': ('get_all_parts_display',),
            'description': 'Автоматично підтягуються з виконаних робіт та прямо доданих запчастин'
        }),
    )

    inlines = [ServiceWorkInline, DirectUsedPartInline, RepairPhotoInline]

    class Media:
        js = ('js/admin/filter_trucks_by_client.js',)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('get-trucks-by-client/', self.admin_site.admin_view(self.get_trucks_by_client), name='get_trucks_by_client'),
        ]
        return custom_urls + urls

    def get_trucks_by_client(self, request):
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

    def get_cost_breakdown(self, obj):
        """Детальна розбивка вартості"""
        if not obj.pk:
            return "Спочатку збережіть замовлення"
        
        from django.utils.html import format_html
        from decimal import Decimal
        
        # Вартість робіт
        works = obj.works.select_related('work__work_group').filter(work__isnull=False)
        total_work_cost = sum(
            work.work.get_calculated_price() * (work.hours_spent or Decimal('1'))
            for work in works
        )
        
        # Запчастини через роботи
        parts_via_works = UsedPart.objects.filter(
            service_work__service_order=obj
        )
        parts_via_works_cost = sum(p.total_price for p in parts_via_works)
        
        # Запчастини додані напряму
        direct_parts = obj.direct_parts.all()
        direct_parts_cost = sum(p.total_price for p in direct_parts)
        
        total_parts_cost = parts_via_works_cost + direct_parts_cost
        
        html = f"""
        <table style='width: 100%; border-collapse: collapse;'>
            <tr style='background: #f0f0f0;'>
                <td style='padding: 8px; font-weight: bold;'>Роботи</td>
                <td style='padding: 8px; text-align: right;'>{total_work_cost:.2f} грн</td>
            </tr>
            <tr>
                <td style='padding: 8px; font-weight: bold;'>Запчастини (всього)</td>
                <td style='padding: 8px; text-align: right;'>{total_parts_cost:.2f} грн</td>
            </tr>
            <tr style='background: #f0f0f0;'>
                <td style='padding: 8px; padding-left: 24px;'>— через роботи</td>
                <td style='padding: 8px; text-align: right;'>{parts_via_works_cost:.2f} грн</td>
            </tr>
            <tr style='background: #f0f0f0;'>
                <td style='padding: 8px; padding-left: 24px;'>— пряме додавання</td>
                <td style='padding: 8px; text-align: right;'>{direct_parts_cost:.2f} грн</td>
            </tr>
            <tr style='background: #e3f2fd; font-weight: bold; font-size: 1.1em;'>
                <td style='padding: 10px;'>РАЗОМ</td>
                <td style='padding: 10px; text-align: right;'>{obj.total_cost:.2f} грн</td>
            </tr>
        </table>
        """
        return format_html(html)
    
    get_cost_breakdown.short_description = 'Розбивка вартості'

    def get_all_parts_display(self, obj):
        """Показує всі запчастини (через роботи + прямі)"""
        if not obj.pk:
            return "Спочатку збережіть замовлення"
        
        from django.utils.html import format_html
        
        # Запчастини через роботи
        parts_via_works = UsedPart.objects.filter(
            service_work__service_order=obj
        ).select_related('part', 'service_work__work')
        
        # Запчастини додані напряму
        direct_parts = obj.direct_parts.select_related('part')
        
        if not parts_via_works and not direct_parts:
            return "Запчастини не додано"
        
        rows = []
        
        # Спочатку запчастини через роботи
        for p in parts_via_works:
            work_name = p.service_work.work.name if p.service_work.work else "—"
            
            part_name_lower = p.part.name.lower()
            is_filter = 'фільтр' in part_name_lower or 'filter' in part_name_lower
            is_oil_liquid = ('олив' in part_name_lower or 'масло' in part_name_lower or 'oil' in part_name_lower)
            
            if is_oil_liquid and not is_filter:
                quantity_display = f"{p.quantity} л"
            else:
                quantity_display = f"{p.quantity} {p.part.unit}"
            
            rows.append(
                f"<tr>"
                f"<td style='padding: 5px; border-bottom: 1px solid #ddd;'>{p.part.sku_code}</td>"
                f"<td style='padding: 5px; border-bottom: 1px solid #ddd;'>{p.part.name}</td>"
                f"<td style='padding: 5px; border-bottom: 1px solid #ddd; text-align: center;'>{quantity_display}</td>"
                f"<td style='padding: 5px; border-bottom: 1px solid #ddd;'>{work_name}</td>"
                f"<td style='padding: 5px; border-bottom: 1px solid #ddd; text-align: right;'>{p.total_price:.2f} грн</td>"
                f"</tr>"
            )
        
        # Потім прямі запчастини
        for p in direct_parts:
            part_name_lower = p.part.name.lower()
            is_filter = 'фільтр' in part_name_lower or 'filter' in part_name_lower
            is_oil_liquid = ('олив' in part_name_lower or 'масло' in part_name_lower or 'oil' in part_name_lower)
            
            if is_oil_liquid and not is_filter:
                quantity_display = f"{p.quantity} л"
            else:
                quantity_display = f"{p.quantity} {p.part.unit}"
            
            rows.append(
                f"<tr style='background: #fff3cd;'>"
                f"<td style='padding: 5px; border-bottom: 1px solid #ddd;'>{p.part.sku_code}</td>"
                f"<td style='padding: 5px; border-bottom: 1px solid #ddd;'>{p.part.name}</td>"
                f"<td style='padding: 5px; border-bottom: 1px solid #ddd; text-align: center;'>{quantity_display}</td>"
                f"<td style='padding: 5px; border-bottom: 1px solid #ddd;'><em>пряме додавання</em></td>"
                f"<td style='padding: 5px; border-bottom: 1px solid #ddd; text-align: right;'>{p.total_price:.2f} грн</td>"
                f"</tr>"
            )
        
        table = f"""
        <table style='width: 100%; border-collapse: collapse;'>
            <thead>
                <tr style='background: #f0f0f0;'>
                    <th style='padding: 8px; text-align: left;'>Артикул</th>
                    <th style='padding: 8px; text-align: left;'>Запчастина</th>
                    <th style='padding: 8px; text-align: center;'>Кількість</th>
                    <th style='padding: 8px; text-align: left;'>Прив'язка</th>
                    <th style='padding: 8px; text-align: right;'>Вартість</th>
                </tr>
            </thead>
            <tbody>
            {''.join(rows)}
            </tbody>
        </table>
        <p style='margin-top: 10px; font-size: 0.9em; color: #666;'>
            <strong>Жовтим</strong> виділені запчастини, додані напряму (без прив'язки до роботи)
        </p>
        """
        return format_html(table)

    get_all_parts_display.short_description = 'Перелік запчастин'

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        # Оновлюємо вартість після збереження будь-якого formset
        if form.instance.pk:
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


@admin.register(ServiceWork)
class ServiceWorkAdmin(admin.ModelAdmin):
    list_display = ('service_order', 'work', 'employee', 'hours_spent')
    autocomplete_fields = ('service_order', 'work', 'employee')
    inlines = [UsedPartInline]
    search_fields = ['description', 'service_order__order_number', 'work__name']
    ordering = ['-service_order']