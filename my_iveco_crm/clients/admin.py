from django.contrib import admin
from .models import Client, Truck, IvecoModel # Додано IvecoModel

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'surname', 'phone', 'email', 'created_at')
    search_fields = ('name', 'surname', 'phone', 'email')

@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = ('client', 'iveco_model', 'license_plate', 'full_vin', 'last_seven_vin', 'current_mileage', 'transmission_type')
    list_filter = ('iveco_model', 'transmission_type', 'year_of_manufacture')
    search_fields = ('full_vin', 'last_seven_vin', 'license_plate', 'client__name', 'client__surname')
    readonly_fields = ('last_seven_vin',) # Робимо поле тільки для читання

@admin.register(IvecoModel)
class IvecoModelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)