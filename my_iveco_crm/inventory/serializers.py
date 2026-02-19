from rest_framework import serializers
from .models import Product, Category, SubCategory, Warehouse, StockItem, StockMovement, UsedPart


class CategorySerializer(serializers.ModelSerializer):
    """Серіалізатор категорій"""
    subcategories_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id',
            'name',
            'slug',
            'category_type',
            'is_active',
            'sort_order',
            'subcategories_count',
        ]

    def get_subcategories_count(self, obj):
        return obj.subcategories.count()


class SubCategorySerializer(serializers.ModelSerializer):
    """Серіалізатор підкатегорій"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_type = serializers.CharField(source='category.category_type', read_only=True)
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = SubCategory
        fields = [
            'id',
            'category',
            'category_name',
            'category_type',
            'name',
            'slug',
            'is_active',
            'default_change_interval_km',
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
            'is_active',
            'is_default',
            'sort_order',
            'stock_count',
        ]

    def get_stock_count(self, obj):
        return obj.stock_items.count()


class ProductSerializer(serializers.ModelSerializer):
    """Серіалізатор товарів"""
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    subcategory_type = serializers.CharField(source='subcategory.category.category_type', read_only=True)
    is_low_stock = serializers.ReadOnlyField()
    marked_for_deletion_by_name = serializers.CharField(
        source='marked_for_deletion_by.get_full_name',
        read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id',
            'sku_code',
            'name',
            'brand',
            'subcategory',
            'subcategory_name',
            'subcategory_type',
            'cost_price',
            'selling_price',
            'current_stock',
            'min_stock_level',
            'unit',
            'is_active',
            'created_at',
            'viscosity',
            'volume_per_unit',
            'specifications',
            'notes',
            'address_in_stock',
            'is_low_stock',
            'marked_for_deletion',
            'marked_for_deletion_by',
            'marked_for_deletion_by_name',
            'marked_for_deletion_at',
            'deletion_reason',
        ]
        read_only_fields = [
            'created_at',
            'is_low_stock',
            'marked_for_deletion',
            'marked_for_deletion_by',
            'marked_for_deletion_at',
            'deletion_reason',
        ]
        extra_kwargs = {
            'notes': {'required': False, 'allow_blank': True, 'default': ''},
        }


class ProductListSerializer(serializers.ModelSerializer):
    """Скорочений серіалізатор для списків"""
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'sku_code',
            'name',
            'brand',
            'subcategory',
            'subcategory_name',
            'unit',
            'selling_price',
            'current_stock',
            'min_stock_level',
            'is_active',
            'marked_for_deletion',
        ]


class StockItemSerializer(serializers.ModelSerializer):
    """Серіалізатор залишків на складі"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku_code', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    available = serializers.ReadOnlyField()

    class Meta:
        model = StockItem
        fields = [
            'id',
            'warehouse',
            'warehouse_name',
            'product',
            'product_name',
            'product_sku',
            'product_unit',
            'quantity',
            'reserved',
            'available',
            'location',
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
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = UsedPart
        fields = [
            'id',
            'service_work',
            'service_order',
            'part',
            'part_name',
            'part_sku',
            'quantity',
            'warehouse',
            'warehouse_name',
            'unit_price',
            'total_price',
        ]