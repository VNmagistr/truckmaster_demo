# maintenance/admin.py

from django.contrib import admin
from django.utils.html import format_html
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
        'next_change_date',
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
    readonly_fields = ['created_at', 'total_price', 'get_interval_info']
    
    # Autocomplete для пошуку Вантажівки, Наряду-замовлення та Товару
    autocomplete_fields = ['truck', 'service_order', 'product', 'subcategory']
    
    fieldsets = (
        ('Вантажівка', {
            'fields': ('truck', 'service_order')
        }),
        ('Заміна', {
            'fields': ('subcategory', 'product', 'quantity', 'mileage', 'performed_at')
        }),
        ('Інтервал заміни', {
            'fields': ('get_interval_info',),
            'description': 'Інформація про інтервали заміни для вибраної підкатегорії'
        }),
        ('Наступна заміна', {
            'fields': ('next_change_mileage', 'next_change_date'),
            'description': 'Заповнюється автоматично, але можна змінити вручну'
        }),
        ('Вартість', {
            'fields': ('unit_price', 'total_price')
        }),
        ('Додатково', {
            'fields': ('notes', 'created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_interval_info(self, obj):
        """Показує інформацію про інтервали заміни"""
        if not obj.subcategory:
            return "—"
        
        interval_km = obj.subcategory.default_change_interval_km
        
        if interval_km:
            html = f"""
            <div style="background: #e3f2fd; padding: 10px; border-radius: 5px;">
                <strong>📊 Інтервал з підкатегорії "{obj.subcategory.name}":</strong><br>
                <ul style="margin: 5px 0;">
                    <li><strong>За пробігом:</strong> {interval_km:,} км</li>
                    <li><strong>За часом:</strong> 1 рік</li>
                </ul>
                <p style="margin: 5px 0; font-size: 0.9em; color: #666;">
                    ℹ️ Якщо поля "Наступна заміна" порожні, вони розрахуються автоматично при збереженні.
                </p>
            </div>
            """
        else:
            html = f"""
            <div style="background: #fff3cd; padding: 10px; border-radius: 5px;">
                <strong>⚠️ Увага:</strong> Для підкатегорії "{obj.subcategory.name}" не встановлено 
                інтервал заміни за замовчуванням.<br>
                <small>Вкажіть значення вручну або налаштуйте інтервал в підкатегорії.</small>
            </div>
            """
        
        return format_html(html)
    
    get_interval_info.short_description = 'Інтервал заміни'
    
    def save_model(self, request, obj, form, change):
        """Автоматично заповнюємо created_by"""
        if not change:  # Якщо новий запис
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


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
    
    # Autocomplete для truck
    autocomplete_fields = ['truck', 'completed_order', 'subcategory']
    
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
    
    # Autocomplete для truck та products
    autocomplete_fields = ['truck', 'recommended_product', 'subcategory']
    
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