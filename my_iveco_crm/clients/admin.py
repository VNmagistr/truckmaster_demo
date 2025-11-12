from django.contrib import admin
from .models import Client, IvecoBaseModel, Truck, OwnershipHistory # 1. Імпортуємо нову модель

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email')
    search_fields = ('name', 'phone')

@admin.register(IvecoBaseModel)
class IvecoBaseModelAdmin(admin.ModelAdmin):
    search_fields = ('name',)

# 2. Створюємо "вбудовану" адмінку для історії
class OwnershipHistoryInline(admin.TabularInline):
    model = OwnershipHistory
    extra = 0 # Не показувати порожні форми
    # Робимо історію доступною тільки для читання
    readonly_fields = ('client', 'license_plate', 'change_date') 
    can_delete = False # Забороняємо видаляти історію

    def has_add_permission(self, request, obj=None):
        return False # Забороняємо додавати історію вручну

# 3. Оновлюємо адмінку Вантажівок
@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = ('license_plate', 'client', 'specific_model_name', 'last_seven_vin')
    search_fields = ('license_plate', 'last_seven_vin', 'client__name')
    list_filter = ('client', 'base_model')
    autocomplete_fields = ('client', 'base_model')

    # 4. Додаємо історію внизу сторінки редагування вантажівки
    inlines = [OwnershipHistoryInline]