from django.contrib import admin
from .models import PartCategory, Part, UsedPart

@admin.register(PartCategory)
class PartCategoryAdmin(admin.ModelAdmin):
    # Додаємо 'parent' у список
    list_display = ('name', 'parent', 'description')
    list_filter = ('parent',) # Додаємо фільтр за батьківською категорією
    search_fields = ('name',)
    # Дозволяє легкий пошук батьківської категорії
    autocomplete_fields = ['parent'] 

@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'sku_code', 'selling_price', 'current_stock')
    search_fields = ('name', 'sku_code')
    # Оновлюємо фільтр, щоб можна було фільтрувати і за батьком
    list_filter = ('category__parent', 'category') 
    list_editable = ('selling_price', 'current_stock')
    # Дозволяє легкий пошук категорії
    autocomplete_fields = ['category'] 

@admin.register(UsedPart)
class UsedPartAdmin(admin.ModelAdmin):
    list_display = ('service_work', 'part', 'quantity')
    # autocomplete_fields потрібні для зручного пошуку
    # у зв'язаних моделях (особливо коли їх багато)
    autocomplete_fields = ['service_work', 'part']