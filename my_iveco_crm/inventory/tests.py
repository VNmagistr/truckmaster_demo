"""
Tests for inventory app - models, categories, parts management
"""
from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal

from .models import PartCategory, Part, UsedPart
from clients.models import Client, IvecoBaseModel, Truck
from orders.models import Employee, WorkGroup, WorkPrice, ServiceOrder, ServiceWork


class PartCategoryModelTest(TestCase):
    """Tests for PartCategory model - hierarchical categories"""
    
    def test_create_root_category(self):
        """Test creating a root category (no parent)"""
        category = PartCategory.objects.create(
            name='Двигун',
            description='Запчастини для двигуна'
        )
        
        self.assertEqual(category.name, 'Двигун')
        self.assertIsNone(category.parent)
        self.assertEqual(str(category), 'Двигун')
    
    def test_create_subcategory(self):
        """Test creating a subcategory with parent"""
        parent = PartCategory.objects.create(name='Двигун')
        child = PartCategory.objects.create(
            name='Фільтри',
            parent=parent,
            description='Фільтри двигуна'
        )
        
        self.assertEqual(child.parent, parent)
        self.assertEqual(str(child), 'Двигун -> Фільтри')
    
    def test_category_hierarchy(self):
        """Test category hierarchy with multiple levels"""
        root = PartCategory.objects.create(name='Двигун')
        filters = PartCategory.objects.create(name='Фільтри', parent=root)
        
        # Check subcategories relation
        self.assertIn(filters, root.subcategories.all())
    
    def test_category_unique_name(self):
        """Test category name uniqueness"""
        PartCategory.objects.create(name='Двигун')
        
        with self.assertRaises(Exception):
            PartCategory.objects.create(name='Двигун')


class PartModelTest(TestCase):
    """Tests for Part model"""
    
    def setUp(self):
        self.category = PartCategory.objects.create(name='Фільтри')
    
    def test_create_part(self):
        """Test creating a part with all fields"""
        part = Part.objects.create(
            category=self.category,
            name='Фільтр оливи',
            sku_code='OIL-FILTER-001',
            description='Масляний фільтр для Daily',
            cost_price=Decimal('150.00'),
            selling_price=Decimal('250.00'),
            current_stock=10,
            address_in_stock='A-1-3',
            notes='Підходить для Euro 5'
        )
        
        self.assertEqual(part.name, 'Фільтр оливи')
        self.assertEqual(part.sku_code, 'OIL-FILTER-001')
        self.assertEqual(part.cost_price, Decimal('150.00'))
        self.assertEqual(part.selling_price, Decimal('250.00'))
        self.assertEqual(part.current_stock, 10)
    
    def test_part_str_representation(self):
        """Test string representation of Part"""
        part = Part.objects.create(
            name='Фільтр оливи',
            sku_code='OIL-001',
            selling_price=Decimal('250.00')
        )
        
        self.assertEqual(str(part), 'Фільтр оливи (OIL-001)')
    
    def test_part_sku_unique(self):
        """Test SKU code uniqueness"""
        Part.objects.create(
            name='Part 1',
            sku_code='SKU-001',
            selling_price=Decimal('100.00')
        )
        
        with self.assertRaises(Exception):
            Part.objects.create(
                name='Part 2',
                sku_code='SKU-001',
                selling_price=Decimal('200.00')
            )
    
    def test_part_substitutes(self):
        """Test part substitutes (analogs) relationship"""
        original = Part.objects.create(
            name='Original Filter',
            sku_code='ORIG-001',
            selling_price=Decimal('300.00')
        )
        analog1 = Part.objects.create(
            name='Analog Filter 1',
            sku_code='ANALOG-001',
            selling_price=Decimal('200.00')
        )
        analog2 = Part.objects.create(
            name='Analog Filter 2',
            sku_code='ANALOG-002',
            selling_price=Decimal('180.00')
        )
        
        original.substitutes.add(analog1, analog2)
        
        self.assertEqual(original.substitutes.count(), 2)
        self.assertIn(analog1, original.substitutes.all())
        self.assertIn(analog2, original.substitutes.all())
    
    def test_part_default_values(self):
        """Test default values for optional fields"""
        part = Part.objects.create(
            name='Minimal Part',
            sku_code='MIN-001',
            selling_price=Decimal('100.00')
        )
        
        self.assertEqual(part.cost_price, Decimal('0'))
        self.assertEqual(part.current_stock, 0)
        self.assertIsNone(part.category)
        self.assertIsNone(part.address_in_stock)
    
    def test_part_ordering(self):
        """Test parts are ordered by name"""
        Part.objects.create(name='Zebra Part', sku_code='Z-001', selling_price=Decimal('100'))
        Part.objects.create(name='Alpha Part', sku_code='A-001', selling_price=Decimal('100'))
        Part.objects.create(name='Beta Part', sku_code='B-001', selling_price=Decimal('100'))
        
        parts = list(Part.objects.all())
        self.assertEqual(parts[0].name, 'Alpha Part')
        self.assertEqual(parts[1].name, 'Beta Part')
        self.assertEqual(parts[2].name, 'Zebra Part')


class UsedPartModelTest(TestCase):
    """Tests for UsedPart model - parts used in service works"""
    
    def setUp(self):
        # Create necessary related objects
        self.client = Client.objects.create(name='Test Client')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )
        
        self.employee = Employee.objects.create(name='John', position='Mechanic')
        self.work_group = WorkGroup.objects.create(name='Engine', hourly_rate=Decimal('500'))
        self.work_price = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Oil Change',
            standard_hours=Decimal('1.0')
        )
        
        self.service_order = ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.client,
            truck=self.truck
        )
        
        self.service_work = ServiceWork.objects.create(
            service_order=self.service_order,
            work=self.work_price,
            employee=self.employee,
            hours_spent=Decimal('1.0')
        )
        
        self.part = Part.objects.create(
            name='Oil Filter',
            sku_code='OIL-F-001',
            selling_price=Decimal('250.00')
        )
    
    def test_create_used_part(self):
        """Test creating a used part record"""
        used_part = UsedPart.objects.create(
            service_work=self.service_work,
            part=self.part,
            quantity=2
        )
        
        self.assertEqual(used_part.service_work, self.service_work)
        self.assertEqual(used_part.part, self.part)
        self.assertEqual(used_part.quantity, 2)
    
    def test_used_part_str_representation(self):
        """Test string representation"""
        used_part = UsedPart.objects.create(
            service_work=self.service_work,
            part=self.part,
            quantity=3
        )
        
        self.assertEqual(str(used_part), 'Oil Filter - 3 шт.')
    
    def test_used_part_unique_together(self):
        """Test that same part can't be added twice to same service work"""
        UsedPart.objects.create(
            service_work=self.service_work,
            part=self.part,
            quantity=1
        )
        
        with self.assertRaises(Exception):
            UsedPart.objects.create(
                service_work=self.service_work,
                part=self.part,
                quantity=2
            )
    
    def test_used_part_protected_deletion(self):
        """Test that part cannot be deleted if used in service work"""
        UsedPart.objects.create(
            service_work=self.service_work,
            part=self.part,
            quantity=1
        )
        
        with self.assertRaises(Exception):
            self.part.delete()
            