# inventory/tests.py

from django.test import TestCase
from decimal import Decimal
from .models import PartCategory, Part, Product, Category, SubCategory, Warehouse, StockItem


class PartCategoryModelTest(TestCase):
    """Test PartCategory model"""

    def test_create_parent_category(self):
        """Test creating a parent category"""
        category = PartCategory.objects.create(
            name='Filters',
            description='All types of filters'
        )
        self.assertEqual(category.name, 'Filters')
        self.assertIsNone(category.parent)

    def test_create_child_category(self):
        """Test creating a child category"""
        parent = PartCategory.objects.create(name='Filters')
        child = PartCategory.objects.create(
            name='Oil Filters',
            parent=parent
        )
        self.assertEqual(child.parent, parent)

    def test_category_str_representation(self):
        """Test string representation of category"""
        parent = PartCategory.objects.create(name='Filters')
        child = PartCategory.objects.create(name='Oil Filters', parent=parent)

        self.assertEqual(str(parent), 'Filters')
        self.assertEqual(str(child), 'Filters -> Oil Filters')


class ProductModelTest(TestCase):
    """Test Product model"""

    def test_create_product(self):
        """Test creating a product"""
        product = Product.objects.create(
            name='Фільтр оливи',
            sku_code='OIL-001',
            cost_price=Decimal('100.00'),
            selling_price=Decimal('150.00'),
            current_stock=10
        )
        self.assertEqual(product.name, 'Фільтр оливи')
        self.assertEqual(product.selling_price, Decimal('150.00'))

    def test_product_str_representation(self):
        """Test string representation of Product"""
        product = Product.objects.create(
            name='Фільтр оливи',
            sku_code='OIL-001',
        )
        self.assertEqual(str(product), 'Фільтр оливи')

    def test_product_str_with_brand(self):
        """Test string representation of Product with brand"""
        product = Product.objects.create(
            name='Фільтр оливи',
            sku_code='OIL-002',
            brand='MANN'
        )
        self.assertEqual(str(product), 'MANN Фільтр оливи')

    def test_product_str_with_viscosity(self):
        """Test string representation of Product with viscosity"""
        product = Product.objects.create(
            name='Моторна олива',
            sku_code='OIL-003',
            viscosity='5W-30'
        )
        self.assertEqual(str(product), 'Моторна олива 5W-30')

    def test_is_low_stock(self):
        """Test low stock detection"""
        product = Product.objects.create(
            name='Фільтр',
            sku_code='F-001',
            current_stock=3,
            min_stock_level=5
        )
        self.assertTrue(product.is_low_stock)

    def test_is_not_low_stock(self):
        """Test normal stock level"""
        product = Product.objects.create(
            name='Фільтр',
            sku_code='F-002',
            current_stock=10,
            min_stock_level=5
        )
        self.assertFalse(product.is_low_stock)


class CategoryModelTest(TestCase):
    """Test Category model"""

    def test_create_category(self):
        """Test creating a category"""
        category = Category.objects.create(
            name='Оливи',
            slug='oils',
            category_type='oil'
        )
        self.assertEqual(category.name, 'Оливи')
        self.assertEqual(category.category_type, 'oil')


class WarehouseModelTest(TestCase):
    """Test Warehouse model"""

    def test_create_warehouse(self):
        """Test creating a warehouse"""
        warehouse = Warehouse.objects.create(
            name='Головний склад',
            slug='main',
            is_default=True
        )
        self.assertEqual(warehouse.name, 'Головний склад')
        self.assertTrue(warehouse.is_default)

    def test_only_one_default_warehouse(self):
        """Test that only one warehouse can be default"""
        wh1 = Warehouse.objects.create(name='Склад 1', slug='wh1', is_default=True)
        wh2 = Warehouse.objects.create(name='Склад 2', slug='wh2', is_default=True)

        wh1.refresh_from_db()
        self.assertFalse(wh1.is_default)
        self.assertTrue(wh2.is_default)


class StockItemModelTest(TestCase):
    """Test StockItem model"""

    def setUp(self):
        self.warehouse = Warehouse.objects.create(name='Склад', slug='main')
        self.product = Product.objects.create(
            name='Фільтр',
            sku_code='F-001',
            min_stock_level=5
        )

    def test_create_stock_item(self):
        """Test creating stock record"""
        stock = StockItem.objects.create(
            warehouse=self.warehouse,
            product=self.product,
            quantity=10
        )
        self.assertEqual(stock.quantity, 10)

    def test_available_quantity(self):
        """Test available quantity calculation"""
        stock = StockItem.objects.create(
            warehouse=self.warehouse,
            product=self.product,
            quantity=10,
            reserved=3
        )
        self.assertEqual(stock.available, 7)
