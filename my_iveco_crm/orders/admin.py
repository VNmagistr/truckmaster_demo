# orders/admin.py

from inventory.models import UsedPart
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
# 1. Прибрали Employee з імпортів
from .models import (
    WorkGroup, ServiceOrder, ServiceWork, 
    RepairPhoto, MaintenanceRule, MaintenanceLog, WorkPrice, MaintenanceKit,
    FilterType, MaintenanceKitFilter
)

# --- INLINES ---

class UsedPartInline(admin.TabularInline):
    """Запчастини прив'язані до роботи"""
    model = UsedPart
    fk_name = 'service_work'
    autocomplete_fields = ['part', 'warehouse']
    extra = 1
    verbose_name = "Запчастина до роботи"
    verbose_name_plural = "Запчастини до роботи"
    fields = ('part', 'quantity', 'warehouse', 'unit_price')
    readonly_fields = ('unit_price',)


class DirectUsedPartInline(admin.TabularInline):
    """Запчастини додані напряму до замовлення"""
    model = UsedPart
    fk_name = 'service_order'
    autocomplete_fields = ['part', 'warehouse']
    extra = 1
    verbose_name = "Запчастина (пряме додавання)"
    verbose_name_plural = "Запчастини (пряме додавання)"
    fields = ('part', 'quantity', 'warehouse', 'unit_price')
    readonly_fields = ('unit_price',)


class ServiceWorkInline(admin.TabularInline):
    model = ServiceWork
    # 2. Замінили employee на mechanic
    autocomplete_fields = ['work', 'mechanic'] 
    extra = 0 # Щоб не займало багато місця
    # 3. Оновили список полів
    fields = ('work', 'mechanic', 'hours_spent', 'description')


class RepairPhotoInline(admin.TabularInline):
    model = RepairPhoto
    extra = 1


# --- GOVNO ADMINS (Main) ---

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
        ('Прийомка (Фото та Пробіг)', {
            'fields': ('current_mileage', 'car_photo', 'odometer_photo', 'dashboard_photo')
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
        ('Службова інформація', {
             'classes': ('collapse',),
             'fields': ('marked_for_deletion', 'deletion_reason')
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
        if not obj.pk: return "Спочатку збережіть замовлення"
        from django.utils.html import format_html
        from decimal import Decimal
        
        # Роботи
        works = obj.works.select_related('work__work_group').filter(work__isnull=False)
        total_work_cost = sum(
            work.work.get_calculated_price() * (work.hours_spent or Decimal('1'))
            for work in works
        )
        
        # Запчастини
        parts_via_works_cost = sum(p.total_price for p in UsedPart.objects.filter(service_work__service_order=obj))
        direct_parts_cost = sum(p.total_price for p in obj.direct_parts.all())
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
            <tr style='background: #e3f2fd; font-weight: bold; font-size: 1.1em;'>
                <td style='padding: 10px;'>РАЗОМ</td>
                <td style='padding: 10px; text-align: right;'>{obj.total_cost:.2f} грн</td>
            </tr>
        </table>
        """
        return format_html(html)
    
    get_cost_breakdown.short_description = 'Розбивка вартості'

    def get_all_parts_display(self, obj):
        if not obj.pk: return "Спочатку збережіть замовлення"
        from django.utils.html import format_html
        
        parts_via_works = UsedPart.objects.filter(service_work__service_order=obj).select_related('part', 'service_work__work')
        direct_parts = obj.direct_parts.select_related('part')
        
        if not parts_via_works and not direct_parts:
            return "Запчастини не додано"
        
        rows = []
        for p in parts_via_works:
            rows.append(
                f"<tr><td style='padding:5px; border-bottom:1px solid #ddd;'>{p.part.name}</td>"
                f"<td style='padding:5px; border-bottom:1px solid #ddd;'>{p.quantity} {p.part.unit}</td>"
                f"<td style='padding:5px; border-bottom:1px solid #ddd;'>{p.service_work.work.name if p.service_work.work else '-'}</td>"
                f"<td style='padding:5px; border-bottom:1px solid #ddd; text-align:right;'>{p.total_price:.2f}</td></tr>"
            )
        for p in direct_parts:
            rows.append(
                f"<tr style='background:#fff3cd;'><td style='padding:5px; border-bottom:1px solid #ddd;'>{p.part.name}</td>"
                f"<td style='padding:5px; border-bottom:1px solid #ddd;'>{p.quantity} {p.part.unit}</td>"
                f"<td style='padding:5px; border-bottom:1px solid #ddd;'><em>пряме</em></td>"
                f"<td style='padding:5px; border-bottom:1px solid #ddd; text-align:right;'>{p.total_price:.2f}</td></tr>"
            )
            
        return format_html(f"<table style='width:100%'>{''.join(rows)}</table>")

    get_all_parts_display.short_description = 'Перелік запчастин'

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        if form.instance.pk:
            form.instance.update_total_cost()


# 4. Видалили EmployeeAdmin, бо моделі вже немає

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
        return f"{obj.get_calculated_price():.2f} грн"
    get_calculated_price.short_description = 'Розрахункова ціна'


@admin.register(ServiceWork)
class ServiceWorkAdmin(admin.ModelAdmin):
    # 5. Замінили employee на mechanic
    list_display = ('service_order', 'work', 'mechanic', 'hours_spent')
    autocomplete_fields = ('service_order', 'work', 'mechanic')
    inlines = [UsedPartInline]
    search_fields = ['description', 'service_order__order_number', 'work__name']
    ordering = ['-service_order']

# Реєструємо інші моделі, якщо вони існують у models.py
try:
    @admin.register(MaintenanceRule)
    class MaintenanceRuleAdmin(admin.ModelAdmin):
        list_display = ['name', 'km_interval']
        search_fields = ['name']
        filter_horizontal = ['applicable_models']
except ImportError:
    pass