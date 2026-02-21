from django.contrib import admin
from .models import Product, Category, SubCategory, Warehouse, StockItem, StockMovement, UsedPart


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'category_type', 'is_active', 'sort_order')
    list_filter = ('category_type', 'is_active')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'slug', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['category']


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_default', 'is_active')
    list_filter = ('is_active', 'is_default')
    search_fields = ('name', 'slug')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku_code', 'brand', 'subcategory', 'selling_price', 'current_stock', 'is_active')
    list_filter = ('subcategory__category', 'subcategory', 'is_active', 'brand')
    search_fields = ('name', 'sku_code', 'brand', 'notes')
    list_editable = ('selling_price', 'current_stock', 'is_active')
    autocomplete_fields = ['subcategory']

    fieldsets = (
        ('Основне', {
            'fields': ('name', 'sku_code', 'brand', 'subcategory')
        }),
        ('Характеристики', {
            'fields': ('viscosity', 'specifications', 'volume_per_unit', 'unit'),
            'classes': ('collapse',)
        }),
        ('Ціни', {
            'fields': ('cost_price', 'selling_price')
        }),
        ('Склад', {
            'fields': ('current_stock', 'min_stock_level', 'address_in_stock')
        }),
        ('Додатково', {
            'fields': ('notes', 'is_active'),
            'classes': ('collapse',)
        }),
    )


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
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
    autocomplete_fields = ['product', 'warehouse_from', 'warehouse_to']
    readonly_fields = ('created_at', 'created_by')
    date_hierarchy = 'created_at'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(UsedPart)
class UsedPartAdmin(admin.ModelAdmin):
    list_display = ('part', 'quantity', 'warehouse', 'unit_price')
    search_fields = ('part__name', 'part__sku_code')
    autocomplete_fields = ['part', 'warehouse']
