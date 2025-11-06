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
    list_display = ('name', 'category', 'sku_code', 'selling_price', 'current_stock')
    search_fields = ('name', 'sku_code')
    list_filter = ('category__parent', 'category') 
    list_editable = ('selling_price', 'current_stock')
    autocomplete_fields = ['category'] 

    # 👇 ДОДАЄМО ЦЕЙ РЯДОК 👇
    # Це створить зручний інтерфейс "вибору" для поля 'substitutes'
    filter_horizontal = ('substitutes',)

@admin.register(UsedPart)
class UsedPartAdmin(admin.ModelAdmin):
    list_display = ('service_work', 'part', 'quantity')
    autocomplete_fields = ['service_work', 'part']