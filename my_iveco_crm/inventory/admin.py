# inventory/admin.py

from django.contrib import admin
from .models import (
    PartCategory, 
    Part, 
    UsedPart,
    ProductCategory,
    ProductSubcategory,
    Warehouse,
    Stock,
    StockMovement,
)


# === Нові моделі ===

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'slug', 'sort_order', 'is_active')
    list_filter = ('category_type', 'is_active')
    search_fields = ('name', 'slug')
    list_editable = ('sort_order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ProductSubcategory)
class ProductSubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'default_change_interval_km', 'sort_order', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'slug')
    list_editable = ('sort_order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['category']


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_default', 'is_active', 'sort_order')
    list_filter = ('is_active', 'is_default')
    search_fields = ('name', 'address')
    list_editable = ('is_default', 'is_active', 'sort_order')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity', 'reserved', 'location', 'updated_at')
    list_filter = ('warehouse',)
    search_fields = ('product__name', 'product__sku_code', 'location')
    autocomplete_fields = ['product', 'warehouse']
    readonly_fields = ('updated_at',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'quantity', 'warehouse_from', 'warehouse_to', 'created_at')
    list_filter = ('movement_type', 'warehouse_from', 'warehouse_to', 'created_at')
    search_fields = ('product__name', 'invoice_number', 'supplier', 'notes')
    
    # ВИПРАВЛЕНО: видалено 'service_order' з autocomplete_fields
    autocomplete_fields = ['product', 'warehouse_from', 'warehouse_to']
    
    readonly_fields = ('created_at', 'created_by')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Тип операції', {
            'fields': ('movement_type',)
        }),
        ('Товар', {
            'fields': ('product', 'quantity')
        }),
        ('Склади', {
            'fields': ('warehouse_from', 'warehouse_to')
        }),
        ('Документи', {
            'fields': ('service_order', 'supplier', 'invoice_number', 'purchase_price'),
            'classes': ('collapse',)
        }),
        ('Додатково', {
            'fields': ('notes', 'created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Тільки при створенні
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# === Старі моделі ===

@admin.register(PartCategory)
class PartCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'description')
    list_filter = ('parent',)
    search_fields = ('name',)
    autocomplete_fields = ['parent']


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku_code', 'subcategory', 'brand', 'selling_price', 'current_stock', 'is_active')
    list_filter = ('subcategory__category', 'subcategory', 'brand', 'is_active')
    search_fields = ('name', 'sku_code', 'brand', 'address_in_stock', 'notes')
    list_editable = ('selling_price', 'current_stock', 'is_active')
    autocomplete_fields = ['category', 'subcategory']
    filter_horizontal = ('substitutes',)
    
    fieldsets = (
        ('Основне', {
            'fields': ('name', 'sku_code', 'brand', 'description')
        }),
        ('Категорії', {
            'fields': ('category', 'subcategory')
        }),
        ('Характеристики (для олив)', {
            'fields': ('viscosity', 'specifications', 'volume_per_unit'),
            'classes': ('collapse',)
        }),
        ('Ціни', {
            'fields': ('cost_price', 'selling_price', 'price_per_liter')
        }),
        ('Склад', {
            'fields': ('unit', 'current_stock', 'min_stock_level', 'address_in_stock')
        }),
        ('Додатково', {
            'fields': ('notes', 'substitutes', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('price_per_liter',)


@admin.register(UsedPart)
class UsedPartAdmin(admin.ModelAdmin):
    list_display = ('service_work', 'part', 'quantity', 'warehouse')
    autocomplete_fields = ['service_work', 'part', 'warehouse']