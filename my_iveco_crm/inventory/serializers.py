# inventory/serializers.py

from rest_framework import serializers
from .models import (
    ProductCategory, 
    ProductSubcategory, 
    Warehouse, 
    Part, 
    Stock, 
    StockMovement,
    PartCategory,
    UsedPart,
)


class ProductCategorySerializer(serializers.ModelSerializer):
    """Серіалізатор категорій товарів"""
    subcategories_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductCategory
        fields = [
            'id', 
            'name', 
            'slug', 
            'category_type', 
            'icon', 
            'sort_order', 
            'is_active',
            'subcategories_count',
        ]
    
    def get_subcategories_count(self, obj):
        return obj.subcategories.count()


class ProductSubcategorySerializer(serializers.ModelSerializer):
    """Серіалізатор підкатегорій"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_type = serializers.CharField(source='category.category_type', read_only=True)
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductSubcategory
        fields = [
            'id',
            'category',
            'category_name',
            'category_type',
            'name',
            'slug',
            'description',
            'sort_order',
            'default_change_interval_km',
            'is_active',
            'products_count',
        ]
    
    def get_products_count(self, obj):
        return obj.products.count()


class WarehouseSerializer(serializers.ModelSerializer):
    """Серіалізатор складів"""
    stock_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Warehouse
        fields = [
            'id',
            'name',
            'slug',
            'address',
            'description',
            'is_active',
            'is_default',
            'sort_order',
            'stock_count',
        ]
    
    def get_stock_count(self, obj):
        return obj.stock_items.count()


class PartCategorySerializer(serializers.ModelSerializer):
    """Серіалізатор старих категорій (для сумісності)"""
    class Meta:
        model = PartCategory
        fields = ['id', 'name', 'description', 'parent']


class PartSerializer(serializers.ModelSerializer):
    """Серіалізатор товарів/запчастин"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    subcategory_type = serializers.CharField(source='subcategory.category.category_type', read_only=True)
    total_stock = serializers.ReadOnlyField()
    is_oil = serializers.ReadOnlyField()
    is_filter = serializers.ReadOnlyField()
    
    class Meta:
        model = Part
        fields = [
            'id',
            'sku_code',
            'name',
            'brand',
            'description',
            'category',
            'category_name',
            'subcategory',
            'subcategory_name',
            'subcategory_type',
            'viscosity',
            'specifications',
            'unit',
            'volume_per_unit',
            'cost_price',
            'selling_price',
            'price_per_liter',
            'current_stock',
            'total_stock',
            'min_stock_level',
            'address_in_stock',
            'notes',
            'is_active',
            'is_oil',
            'is_filter',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'price_per_liter']


class PartListSerializer(serializers.ModelSerializer):
    """Скорочений серіалізатор для списків"""
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    subcategory_type = serializers.CharField(source='subcategory.category.category_type', read_only=True)
    
    class Meta:
        model = Part
        fields = [
            'id',
            'sku_code',
            'name',
            'brand',
            'viscosity',
            'subcategory',
            'subcategory_name',
            'subcategory_type',
            'unit',
            'selling_price',
            'price_per_liter',
            'current_stock',
            'min_stock_level',
            'is_active',
        ]


class StockSerializer(serializers.ModelSerializer):
    """Серіалізатор залишків на складі"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku_code', read_only=True)
    product_brand = serializers.CharField(source='product.brand', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    product_price = serializers.DecimalField(
        source='product.selling_price', 
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )
    product_min_stock = serializers.DecimalField(
        source='product.min_stock_level',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    product_category = serializers.CharField(
        source='product.subcategory.name', 
        read_only=True
    )
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    available = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = Stock
        fields = [
            'id',
            'warehouse',
            'warehouse_name',
            'product',
            'product_id',
            'product_name',
            'product_sku',
            'product_brand',
            'product_unit',
            'product_price',
            'product_min_stock',
            'product_category',
            'quantity',
            'reserved',
            'available',
            'location',
            'is_low_stock',
            'updated_at',
        ]
        read_only_fields = ['updated_at']


class StockMovementSerializer(serializers.ModelSerializer):
    """Серіалізатор руху товарів"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku_code', read_only=True)
    warehouse_from_name = serializers.CharField(source='warehouse_from.name', read_only=True)
    warehouse_to_name = serializers.CharField(source='warehouse_to.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = [
            'id',
            'movement_type',
            'movement_type_display',
            'product',
            'product_name',
            'product_sku',
            'quantity',
            'warehouse_from',
            'warehouse_from_name',
            'warehouse_to',
            'warehouse_to_name',
            'service_order',
            'supplier',
            'invoice_number',
            'purchase_price',
            'notes',
            'created_by',
            'created_by_name',
            'created_at',
        ]
        read_only_fields = ['created_by', 'created_at']


class UsedPartSerializer(serializers.ModelSerializer):
    """Серіалізатор використаних запчастин"""
    part_name = serializers.CharField(source='part.name', read_only=True)
    part_sku = serializers.CharField(source='part.sku_code', read_only=True)
    part_price = serializers.DecimalField(
        source='part.selling_price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = UsedPart
        fields = [
            'id',
            'service_work',
            'part',
            'part_name',
            'part_sku',
            'part_price',
            'quantity',
            'warehouse',
            'warehouse_name',
            'total_price',
        ]
    
    def get_total_price(self, obj):
        return obj.quantity * obj.part.selling_price