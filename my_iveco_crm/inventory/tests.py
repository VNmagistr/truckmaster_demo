# inventory/tests.py

from django.test import TestCase
from decimal import Decimal
from .models import PartCategory, Part, ProductCategory, ProductSubcategory, Warehouse, Stock


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


class PartModelTest(TestCase):
    """Test Part model"""
    
    def setUp(self):
        self.category = PartCategory.objects.create(name='Filters')
    
    def test_create_part(self):
        """Test creating a part"""
        part = Part.objects.create(
            name='Фільтр оливи',
            sku_code='OIL-001',
            category=self.category,
            cost_price=Decimal('100.00'),
            selling_price=Decimal('150.00'),
            current_stock=10
        )
        self.assertEqual(part.name, 'Фільтр оливи')
        self.assertEqual(part.selling_price, Decimal('150.00'))
    
    def test_part_str_representation(self):
        """Test string representation of Part"""
        part = Part.objects.create(
            name='Фільтр оливи',
            sku_code='OIL-001',
            category=self.category
        )
        # Part.__str__ повертає тільки name (плюс brand та viscosity якщо є)
        self.assertEqual(str(part), 'Фільтр оливи')
    
    def test_part_str_with_brand(self):
        """Test string representation of Part with brand"""
        part = Part.objects.create(
            name='Фільтр оливи',
            sku_code='OIL-002',
            category=self.category,
            brand='MANN'
        )
        self.assertEqual(str(part), 'MANN Фільтр оливи')
    
    def test_part_str_with_viscosity(self):
        """Test string representation of Part with viscosity"""
        part = Part.objects.create(
            name='Моторна олива',
            sku_code='OIL-003',
            category=self.category,
            viscosity='5W-30'
        )
        self.assertEqual(str(part), 'Моторна олива 5W-30')
    
    def test_part_price_per_liter_calculation(self):
        """Test automatic price per liter calculation"""
        part = Part.objects.create(
            name='Олива',
            sku_code='OIL-004',
            category=self.category,
            selling_price=Decimal('1000.00'),
            volume_per_unit=Decimal('20.00'),
            unit='l'
        )
        self.assertEqual(part.price_per_liter, Decimal('50.00'))


class ProductCategoryModelTest(TestCase):
    """Test ProductCategory model"""
    
    def test_create_category(self):
        """Test creating a product category"""
        category = ProductCategory.objects.create(
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


class StockModelTest(TestCase):
    """Test Stock model"""
    
    def setUp(self):
        self.warehouse = Warehouse.objects.create(name='Склад', slug='main')
        self.category = PartCategory.objects.create(name='Filters')
        self.part = Part.objects.create(
            name='Фільтр',
            sku_code='F-001',
            category=self.category,
            min_stock_level=5
        )
    
    def test_create_stock(self):
        """Test creating stock record"""
        stock = Stock.objects.create(
            warehouse=self.warehouse,
            product=self.part,
            quantity=10
        )
        self.assertEqual(stock.quantity, 10)
    
    def test_available_quantity(self):
        """Test available quantity calculation"""
        stock = Stock.objects.create(
            warehouse=self.warehouse,
            product=self.part,
            quantity=10,
            reserved=3
        )
        self.assertEqual(stock.available, 7)
    
    def test_low_stock_detection(self):
        """Test low stock detection"""
        stock = Stock.objects.create(
            warehouse=self.warehouse,
            product=self.part,
            quantity=3  # Less than min_stock_level (5)
        )
        self.assertTrue(stock.is_low_stock)
