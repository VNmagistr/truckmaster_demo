# clients/admin.py

from django.contrib import admin
from .models import IvecoBaseModel, Client, Truck

@admin.register(IvecoBaseModel)
class IvecoBaseModelAdmin(admin.ModelAdmin):
    """
    Налаштування адмін-панелі для довідника базових моделей Iveco.
    """
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """
    Налаштування адмін-панелі для моделі Клієнта.
    """
    list_display = ('name', 'surname', 'phone', 'created_at')
    search_fields = ('name', 'surname', 'phone', 'email')
    list_filter = ('created_at',)

@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    """
    Налаштування адмін-панелі для моделі Вантажівки.
    """
    # Поля для відображення у списку вантажівок
    list_display = (
        'specific_model_name', 
        'license_plate', 
        'client', 
        'base_model', 
        'current_mileage'
    )
    
    # Фільтри, що з'являться праворуч
    list_filter = (
        'base_model', 
        'transmission_type', 
        'emission_standard', 
        'year_of_manufacture'
    )
    
    # Поля, за якими можна здійснювати пошук
    search_fields = (
        'license_plate', 
        'full_vin', 
        'last_seven_vin', 
        'specific_model_name',
        'client__name', # Дозволяє шукати за ім'ям клієнта
        'client__surname' # Дозволяє шукати за прізвищем клієнта
    )
    
    # Поля, які не можна редагувати (оскільки вони розраховуються автоматично)
    readonly_fields = ('last_seven_vin',)
    
    # Покращує вибір клієнта, замінюючи випадаючий список на поле пошуку
    # (особливо корисно, коли клієнтів стане багато)
    autocomplete_fields = ['client', 'base_model']

    # Групування полів на сторінці редагування для кращої організації
    fieldsets = (
        ('Основна інформація', {
            'fields': ('client', 'license_plate')
        }),
        ('Ідентифікація моделі', {
            'fields': ('base_model', 'specific_model_name')
        }),
        ('VIN-код', {
            'fields': ('full_vin', 'last_seven_vin')
        }),
        ('Технічні характеристики', {
            'fields': (
                'year_of_manufacture', 
                'transmission_type', 
                'emission_standard', 
                'current_mileage'
            )
        }),
    )