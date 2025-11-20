from django.contrib import admin
from .models import Client, IvecoBaseModel, Truck, OwnershipHistory

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email')
    # 👇 ДОДАНО ЦЕЙ РЯДОК (вирішує помилку autocomplete) 👇
    search_fields = ('name', 'phone', 'email')

@admin.register(IvecoBaseModel)
class IvecoBaseModelAdmin(admin.ModelAdmin):
    # 👇 ДОДАНО ЦЕЙ РЯДОК (на майбутнє) 👇
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
    list_display = ('license_plate', 'client', 'specific_model_name', 'euro_standard', 'last_seven_vin')
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
    