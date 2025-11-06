from django.contrib import admin
from .models import PartCategory, Part, UsedPart

# 1. Реєструємо нову модель Категорій
@admin.register(PartCategory)
class PartCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

# 2. Оновлюємо адмінку для Запчастин
@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'sku_code', 'selling_price', 'current_stock')
    search_fields = ('name', 'sku_code')
    # 👇 Додаємо фільтр за категорією збоку 👇
    list_filter = ('category',)
    list_editable = ('selling_price', 'current_stock')

# 3. Адмінка для Використаних запчастин (без змін)
@admin.register(UsedPart)
class UsedPartAdmin(admin.ModelAdmin):
    list_display = ('service_work', 'part', 'quantity')
    autocomplete_fields = ['service_work', 'part']