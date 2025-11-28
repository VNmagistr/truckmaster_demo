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
)


class ProductCategorySerializer(serializers.ModelSerializer):
    """Серіалізатор категорій товарів"""
    
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
        ]


class ProductSubcategorySerializer(serializers.ModelSerializer):
    """Серіалізатор підкатегорій"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_type = serializers.CharField(source='category.category_type', read_only=True)
    
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
        ]


class WarehouseSerializer(serializers.ModelSerializer):
    """Серіалізатор складів"""
    
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
        ]


class PartCategorySerializer(serializers.ModelSerializer):
    """Серіалізатор старих категорій"""
    
    class Meta:
        model = PartCategory
        fields = ['id', 'name', 'description', 'parent']


class PartSerializer(serializers.ModelSerializer):
    """Серіалізатор товарів/запчастин"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.SerializerMethodField()
    subcategory_type = serializers.SerializerMethodField()
    
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
            'min_stock_level',
            'address_in_stock',
            'notes',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'price_per_liter']
    
    def get_subcategory_name(self, obj):
        if obj.subcategory:
            return obj.subcategory.name
        return None
    
    def get_subcategory_type(self, obj):
        if obj.subcategory and obj.subcategory.category:
            return obj.subcategory.category.category_type
        return None


class PartListSerializer(serializers.ModelSerializer):
    """Скорочений серіалізатор для списків"""
    subcategory_name = serializers.SerializerMethodField()
    subcategory_type = serializers.SerializerMethodField()
    
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
    
    def get_subcategory_name(self, obj):
        if obj.subcategory:
            return obj.subcategory.name
        return None
    
    def get_subcategory_type(self, obj):
        if obj.subcategory and obj.subcategory.category:
            return obj.subcategory.category.category_type
        return None


class StockSerializer(serializers.ModelSerializer):
    """Серіалізатор залишків на складі"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku_code', read_only=True)
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
    product_category = serializers.SerializerMethodField()
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    available = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    
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
    
    def get_product_category(self, obj):
        if obj.product and obj.product.subcategory:
            return obj.product.subcategory.name
        return None
    
    def get_available(self, obj):
        return obj.quantity - obj.reserved
    
    def get_is_low_stock(self, obj):
        if obj.product and obj.product.min_stock_level:
            return obj.quantity <= obj.product.min_stock_level
        return False


class StockMovementSerializer(serializers.ModelSerializer):
    """Серіалізатор руху товарів"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku_code', read_only=True)
    warehouse_from_name = serializers.SerializerMethodField()
    warehouse_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
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
    
    def get_warehouse_from_name(self, obj):
        if obj.warehouse_from:
            return obj.warehouse_from.name
        return None
    
    def get_warehouse_to_name(self, obj):
        if obj.warehouse_to:
            return obj.warehouse_to.name
        return None
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None
