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
    list_display = ('license_plate', 'client', 'specific_model_name', 'last_seven_vin')
    
    # 👇 ДОДАНО ЦЕЙ РЯДОК (вирішує помилку autocomplete) 👇
    search_fields = ('license_plate', 'last_seven_vin', 'client__name', 'specific_model_name', 'full_vin')
    
    list_filter = ('client', 'base_model')
    autocomplete_fields = ('client', 'base_model')
    
    inlines = [OwnershipHistoryInline]