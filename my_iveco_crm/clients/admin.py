from django.contrib import admin
from django.utils.html import format_html
from .models import Client, IvecoBaseModel, Truck, OwnershipHistory

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email')
    search_fields = ('name', 'phone', 'email')

@admin.register(IvecoBaseModel)
class IvecoBaseModelAdmin(admin.ModelAdmin):
    search_fields = ('name',)

class OwnershipHistoryInline(admin.TabularInline):
    model = OwnershipHistory
    extra = 0 
    readonly_fields = ('client', 'license_plate', 'change_date') 
    can_delete = False 

    def has_add_permission(self, request, obj=None):
        return False 

@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = (
        'license_plate', 
        'client', 
        'specific_model_name', 
        'euro_standard', 
        'last_seven_vin', 
        'colored_vin'  # ✅ Додано кольорове позначення VIN
    )
    search_fields = ('license_plate', 'last_seven_vin', 'client__name', 'specific_model_name', 'full_vin')
    list_filter = ('client', 'base_model', 'euro_standard')
    autocomplete_fields = ('client', 'base_model')
    
    # last_seven_vin показуємо тільки для читання
    readonly_fields = ('last_seven_vin',)
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('client', 'base_model', 'specific_model_name', 'euro_standard')
        }),
        ('VIN код', {
            'fields': ('full_vin', 'last_seven_vin'),
            'description': 'Останні 7 символів розраховуються автоматично'
        }),
        ('Реєстрація', {
            'fields': ('license_plate',)
        }),
    )
    
    inlines = [OwnershipHistoryInline]

    def colored_vin(self, obj):
        """
        Виділяє червоним кольором вантажівки з неповним VIN кодом.
        Неповний VIN починається з 'XXXXXXXX' або 'TEMP'.
        """
        if obj.full_vin.startswith('XXXXXXXX') or obj.full_vin.startswith('TEMP'):
            return format_html(
                '<span style="background-color: #ffcccc; color: #cc0000; font-weight: bold; '
                'padding: 3px 8px; border-radius: 3px; display: inline-block;">'
                '⚠️ {}'
                '</span>',
                obj.full_vin
            )
        else:
            return format_html(
                '<span style="color: #28a745; font-weight: normal;">{}</span>',
                obj.full_vin
            )
    
    colored_vin.short_description = 'VIN код (повний)'
    colored_vin.admin_order_field = 'full_vin'  # Дозволяє сортування

    def get_search_results(self, request, queryset, search_term):
        """
        Фільтрує вантажівки по клієнту при autocomplete в ServiceOrder.
        Якщо в URL є параметр client_id - показуємо тільки вантажівки цього клієнта.
        """
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        
        # Перевіряємо чи є фільтр по клієнту в GET параметрах
        # Django admin autocomplete передає forward параметри
        client_id = request.GET.get('client_id')
        
        # Також перевіряємо referer URL на наявність client
        referer = request.META.get('HTTP_REFERER', '')
        if not client_id and 'serviceorder' in referer.lower():
            # Спробуємо отримати client_id з форми через forward
            forward = request.GET.get('forward')
            if forward:
                import json
                try:
                    forward_data = json.loads(forward)
                    client_id = forward_data.get('client')
                except (json.JSONDecodeError, TypeError):
                    pass
        
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        return queryset, use_distinct