from django.contrib import admin
from .models import PartCategory, Part, UsedPart

@admin.register(PartCategory)
class PartCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'description')
    list_filter = ('parent',) 
    search_fields = ('name',)
    autocomplete_fields = ['parent'] 

@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    # 👇 Додаємо 'address_in_stock' до списку 👇
    list_display = ('name', 'category', 'sku_code', 'selling_price', 'current_stock', 'address_in_stock')
    search_fields = ('name', 'sku_code', 'address_in_stock', 'notes') # Додаємо поля для пошуку
    list_filter = ('category__parent', 'category') 
    list_editable = ('selling_price', 'current_stock', 'address_in_stock') # Додаємо в редаговані
    autocomplete_fields = ['category'] 
    filter_horizontal = ('substitutes',)

    # Оновлюємо, щоб нові поля були в формі редагування
    fieldsets = (
        (None, {
            'fields': ('name', 'sku_code', 'category', 'current_stock')
        }),
        ('Ціни', {
            'fields': ('cost_price', 'selling_price')
        }),
        ('Інформація про зберігання', {
            'fields': ('address_in_stock', 'notes')
        }),
        ('Опис та аналоги', {
            'fields': ('description', 'substitutes')
        }),
    )

@admin.register(UsedPart)
class UsedPartAdmin(admin.ModelAdmin):
    list_display = ('service_work', 'part', 'quantity')
    autocomplete_fields = ['service_work', 'part']