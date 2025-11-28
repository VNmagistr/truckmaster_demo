# inventory/serializers.py

from rest_framework import serializers
from .models import (
<<<<<<< HEAD
    ProductCategory,
    ProductSubcategory,
    Warehouse,
    Part,
    Stock,
    StockMovement,
    PartCategory,
=======
    ProductCategory, 
    ProductSubcategory, 
    Warehouse, 
    Part, 
    Stock, 
    StockMovement,
    PartCategory,
    UsedPart,
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
)


class ProductCategorySerializer(serializers.ModelSerializer):
    """Серіалізатор категорій товарів"""
<<<<<<< HEAD
=======
    subcategories_count = serializers.SerializerMethodField()
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
    
    class Meta:
        model = ProductCategory
        fields = [
<<<<<<< HEAD
            'id',
            'name',
            'slug',
            'category_type',
            'icon',
            'sort_order',
            'is_active',
        ]
=======
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
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d


class ProductSubcategorySerializer(serializers.ModelSerializer):
    """Серіалізатор підкатегорій"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_type = serializers.CharField(source='category.category_type', read_only=True)
<<<<<<< HEAD
=======
    products_count = serializers.SerializerMethodField()
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
    
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
<<<<<<< HEAD
        ]
=======
            'products_count',
        ]
    
    def get_products_count(self, obj):
        return obj.products.count()
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d


class WarehouseSerializer(serializers.ModelSerializer):
    """Серіалізатор складів"""
<<<<<<< HEAD
=======
    stock_count = serializers.SerializerMethodField()
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
    
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
<<<<<<< HEAD
        ]


class PartCategorySerializer(serializers.ModelSerializer):
    """Серіалізатор старих категорій"""
    
=======
            'stock_count',
        ]
    
    def get_stock_count(self, obj):
        return obj.stock_items.count()


class PartCategorySerializer(serializers.ModelSerializer):
    """Серіалізатор старих категорій (для сумісності)"""
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
    class Meta:
        model = PartCategory
        fields = ['id', 'name', 'description', 'parent']


class PartSerializer(serializers.ModelSerializer):
    """Серіалізатор товарів/запчастин"""
    category_name = serializers.CharField(source='category.name', read_only=True)
<<<<<<< HEAD
    subcategory_name = serializers.SerializerMethodField()
    subcategory_type = serializers.SerializerMethodField()
=======
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    subcategory_type = serializers.CharField(source='subcategory.category.category_type', read_only=True)
    total_stock = serializers.ReadOnlyField()
    is_oil = serializers.ReadOnlyField()
    is_filter = serializers.ReadOnlyField()
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
    
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
<<<<<<< HEAD
=======
            'total_stock',
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
            'min_stock_level',
            'address_in_stock',
            'notes',
            'is_active',
<<<<<<< HEAD
=======
            'is_oil',
            'is_filter',
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'price_per_liter']
<<<<<<< HEAD
    
    def get_subcategory_name(self, obj):
        if obj.subcategory:
            return obj.subcategory.name
        return None
    
    def get_subcategory_type(self, obj):
        if obj.subcategory and obj.subcategory.category:
            return obj.subcategory.category.category_type
        return None
=======
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d


class PartListSerializer(serializers.ModelSerializer):
    """Скорочений серіалізатор для списків"""
<<<<<<< HEAD
    subcategory_name = serializers.SerializerMethodField()
    subcategory_type = serializers.SerializerMethodField()
=======
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    subcategory_type = serializers.CharField(source='subcategory.category.category_type', read_only=True)
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
    
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
<<<<<<< HEAD
    
    def get_subcategory_name(self, obj):
        if obj.subcategory:
            return obj.subcategory.name
        return None
    
    def get_subcategory_type(self, obj):
        if obj.subcategory and obj.subcategory.category:
            return obj.subcategory.category.category_type
        return None
=======
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d


class StockSerializer(serializers.ModelSerializer):
    """Серіалізатор залишків на складі"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku_code', read_only=True)
<<<<<<< HEAD
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    product_price = serializers.DecimalField(
        source='product.selling_price',
        max_digits=10,
        decimal_places=2,
=======
    product_brand = serializers.CharField(source='product.brand', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    product_price = serializers.DecimalField(
        source='product.selling_price', 
        max_digits=10, 
        decimal_places=2, 
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
        read_only=True
    )
    product_min_stock = serializers.DecimalField(
        source='product.min_stock_level',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
<<<<<<< HEAD
    product_category = serializers.SerializerMethodField()
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    available = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
=======
    product_category = serializers.CharField(
        source='product.subcategory.name', 
        read_only=True
    )
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    available = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
    
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
<<<<<<< HEAD
=======
            'product_brand',
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
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
<<<<<<< HEAD
    
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
=======
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d


class StockMovementSerializer(serializers.ModelSerializer):
    """Серіалізатор руху товарів"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku_code', read_only=True)
<<<<<<< HEAD
    warehouse_from_name = serializers.SerializerMethodField()
    warehouse_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
=======
    warehouse_from_name = serializers.CharField(source='warehouse_from.name', read_only=True)
    warehouse_to_name = serializers.CharField(source='warehouse_to.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
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
<<<<<<< HEAD
    
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
=======


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
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
