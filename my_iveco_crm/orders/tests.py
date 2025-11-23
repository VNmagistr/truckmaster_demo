"""
Tests for orders app - models, business logic, price calculations
"""
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal

from .models import (
    Employee, WorkGroup, WorkPrice, ServiceOrder, ServiceWork,
    RepairPhoto, MaintenanceRule, MaintenanceLog,
    FilterType, MaintenanceKit, MaintenanceKitFilter
)
from clients.models import Client, IvecoBaseModel, Truck
from inventory.models import Part, UsedPart


class EmployeeModelTest(TestCase):
    """Tests for Employee model"""
    
    def test_create_employee(self):
        """Test creating an employee"""
        employee = Employee.objects.create(
            name='Іван Петренко',
            position='Механік'
        )
        
        self.assertEqual(employee.name, 'Іван Петренко')
        self.assertEqual(employee.position, 'Механік')
    
    def test_employee_str_representation(self):
        """Test string representation"""
        employee = Employee.objects.create(name='Іван', position='Механік')
        self.assertEqual(str(employee), 'Іван (Механік)')
    
    def test_employee_ordering(self):
        """Test employees are ordered by name"""
        Employee.objects.create(name='Ярослав', position='Механік')
        Employee.objects.create(name='Андрій', position='Електрик')
        
        employees = list(Employee.objects.all())
        self.assertEqual(employees[0].name, 'Андрій')
        self.assertEqual(employees[1].name, 'Ярослав')


class WorkGroupModelTest(TestCase):
    """Tests for WorkGroup model - work categories with hourly rates"""
    
    def test_create_work_group(self):
        """Test creating a work group"""
        group = WorkGroup.objects.create(
            name='Двигун',
            hourly_rate=Decimal('600.00')
        )
        
        self.assertEqual(group.name, 'Двигун')
        self.assertEqual(group.hourly_rate, Decimal('600.00'))
    
    def test_work_group_str_representation(self):
        """Test string representation includes rate"""
        group = WorkGroup.objects.create(name='Двигун', hourly_rate=Decimal('600'))
        self.assertEqual(str(group), 'Двигун (600 грн/год)')
    
    def test_work_group_default_rate(self):
        """Test default hourly rate"""
        group = WorkGroup.objects.create(name='Загальні')
        self.assertEqual(group.hourly_rate, Decimal('500'))


class WorkPriceModelTest(TestCase):
    """Tests for WorkPrice model - work items with calculated prices"""
    
    def setUp(self):
        self.work_group = WorkGroup.objects.create(
            name='Двигун',
            hourly_rate=Decimal('600.00')
        )
    
    def test_create_work_price(self):
        """Test creating a work price item"""
        work = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Заміна оливи',
            standard_hours=Decimal('1.5')
        )
        
        self.assertEqual(work.name, 'Заміна оливи')
        self.assertEqual(work.standard_hours, Decimal('1.5'))
    
    def test_calculated_price(self):
        """Test price calculation: standard_hours × hourly_rate"""
        work = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Заміна оливи',
            standard_hours=Decimal('1.5')
        )
        
        # 1.5 hours × 600 грн/год = 900 грн
        self.assertEqual(work.get_calculated_price(), Decimal('900.00'))
    
    def test_calculated_price_property(self):
        """Test price property returns calculated price"""
        work = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Діагностика',
            standard_hours=Decimal('0.5')
        )
        
        # 0.5 hours × 600 грн/год = 300 грн
        self.assertEqual(work.price, Decimal('300.00'))
    
    def test_work_price_str_representation(self):
        """Test string representation"""
        work = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Заміна оливи',
            standard_hours=Decimal('1.5')
        )
        
        self.assertIn('Заміна оливи', str(work))
        self.assertIn('1.5', str(work))


class ServiceOrderModelTest(TestCase):
    """Tests for ServiceOrder model"""
    
    def setUp(self):
        self.client = Client.objects.create(name='Test Transport LLC')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )
    
    def test_create_service_order(self):
        """Test creating a service order"""
        order = ServiceOrder.objects.create(
            order_number='ORD-2024-001',
            client=self.client,
            truck=self.truck,
            problem_description='Стук в двигуні'
        )
        
        self.assertEqual(order.order_number, 'ORD-2024-001')
        self.assertEqual(order.client, self.client)
        self.assertEqual(order.truck, self.truck)
        self.assertEqual(order.status, ServiceOrder.StatusChoices.OPEN)
    
    def test_service_order_default_status(self):
        """Test default status is OPEN"""
        order = ServiceOrder.objects.create(client=self.client, truck=self.truck)
        self.assertEqual(order.status, 'OPEN')
    
    def test_service_order_status_choices(self):
        """Test all status choices work"""
        statuses = ['OPEN', 'IN_PROGRESS', 'CLOSED', 'CANCELED']
        
        for i, status in enumerate(statuses):
            order = ServiceOrder.objects.create(
                order_number=f'ORD-{i}',
                client=self.client,
                truck=self.truck,
                status=status
            )
            self.assertEqual(order.status, status)
    
    def test_service_order_str_representation(self):
        """Test string representation"""
        order = ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.client,
            truck=self.truck
        )
        
        self.assertIn('ORD-001', str(order))
        self.assertIn('Test Transport', str(order))
    
    def test_service_order_ordering(self):
        """Test orders are ordered by created_at descending"""
        order1 = ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.client,
            truck=self.truck
        )
        order2 = ServiceOrder.objects.create(
            order_number='ORD-002',
            client=self.client,
            truck=self.truck
        )
        
        orders = list(ServiceOrder.objects.all())
        # Newest first
        self.assertEqual(orders[0], order2)
        self.assertEqual(orders[1], order1)


class ServiceOrderTotalCostTest(TestCase):
    """Tests for ServiceOrder.update_total_cost() method"""
    
    def setUp(self):
        self.client = Client.objects.create(name='Test Client')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )
        
        self.employee = Employee.objects.create(name='Mechanic', position='Mechanic')
        self.work_group = WorkGroup.objects.create(name='Engine', hourly_rate=Decimal('500'))
        
        self.work_price = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Oil Change',
            standard_hours=Decimal('1.0')
        )
        
        self.part = Part.objects.create(
            name='Oil Filter',
            sku_code='OIL-001',
            selling_price=Decimal('200.00')
        )
        
        self.service_order = ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.client,
            truck=self.truck
        )
    
    def test_update_total_cost_with_work_only(self):
        """Test total cost calculation with only work (no parts)"""
        ServiceWork.objects.create(
            service_order=self.service_order,
            work=self.work_price,
            employee=self.employee,
            hours_spent=Decimal('2.0')
        )
        
        total = self.service_order.update_total_cost()
        
        # Work price: 1.0 standard hours × 500 rate = 500
        # Hours spent: 2.0
        # Total: 500 × 2 = 1000
        self.assertEqual(total, Decimal('1000.00'))
    
    def test_update_total_cost_with_parts(self):
        """Test total cost calculation with work and parts"""
        service_work = ServiceWork.objects.create(
            service_order=self.service_order,
            work=self.work_price,
            employee=self.employee,
            hours_spent=Decimal('1.0')
        )
        
        UsedPart.objects.create(
            service_work=service_work,
            part=self.part,
            quantity=2
        )
        
        total = self.service_order.update_total_cost()
        
        # Work: 500 × 1 = 500
        # Parts: 200 × 2 = 400
        # Total: 900
        self.assertEqual(total, Decimal('900.00'))
    
    def test_update_total_cost_multiple_works_and_parts(self):
        """Test total cost with multiple works and parts"""
        work2 = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Diagnostics',
            standard_hours=Decimal('0.5')
        )
        part2 = Part.objects.create(
            name='Air Filter',
            sku_code='AIR-001',
            selling_price=Decimal('150.00')
        )
        
        sw1 = ServiceWork.objects.create(
            service_order=self.service_order,
            work=self.work_price,
            employee=self.employee,
            hours_spent=Decimal('1.0')
        )
        sw2 = ServiceWork.objects.create(
            service_order=self.service_order,
            work=work2,
            employee=self.employee,
            hours_spent=Decimal('1.0')
        )
        
        UsedPart.objects.create(service_work=sw1, part=self.part, quantity=1)
        UsedPart.objects.create(service_work=sw2, part=part2, quantity=3)
        
        total = self.service_order.update_total_cost()
        
        # Work 1: 500 × 1 = 500
        # Work 2: 250 × 1 = 250
        # Part 1: 200 × 1 = 200
        # Part 2: 150 × 3 = 450
        # Total: 1400
        self.assertEqual(total, Decimal('1400.00'))
    
    def test_update_total_cost_empty_order(self):
        """Test total cost for order without works"""
        total = self.service_order.update_total_cost()
        self.assertEqual(total, Decimal('0'))


class ServiceWorkModelTest(TestCase):
    """Tests for ServiceWork model"""
    
    def setUp(self):
        self.client = Client.objects.create(name='Test Client')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )
        self.employee = Employee.objects.create(name='Mechanic', position='Mechanic')
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
    
    def test_create_service_work(self):
        """Test creating a service work record"""
        work = ServiceWork.objects.create(
            service_order=self.service_order,
            work=self.work_price,
            employee=self.employee,
            hours_spent=Decimal('1.5'),
            description='Замінено оливу та фільтр'
        )
        
        self.assertEqual(work.service_order, self.service_order)
        self.assertEqual(work.work, self.work_price)
        self.assertEqual(work.hours_spent, Decimal('1.5'))
    
    def test_service_work_default_hours(self):
        """Test default hours spent is 1"""
        work = ServiceWork.objects.create(
            service_order=self.service_order,
            work=self.work_price,
            employee=self.employee
        )
        
        self.assertEqual(work.hours_spent, Decimal('1'))


class MaintenanceRuleModelTest(TestCase):
    """Tests for MaintenanceRule model"""
    
    def setUp(self):
        self.base_model1 = IvecoBaseModel.objects.create(name='Daily')
        self.base_model2 = IvecoBaseModel.objects.create(name='Eurocargo')
    
    def test_create_maintenance_rule(self):
        """Test creating a maintenance rule"""
        rule = MaintenanceRule.objects.create(
            name='Заміна оливи',
            description='Заміна моторної оливи та фільтра',
            km_interval=15000
        )
        rule.applicable_models.add(self.base_model1, self.base_model2)
        
        self.assertEqual(rule.name, 'Заміна оливи')
        self.assertEqual(rule.km_interval, 15000)
        self.assertEqual(rule.applicable_models.count(), 2)
    
    def test_maintenance_rule_str_representation(self):
        """Test string representation"""
        rule = MaintenanceRule.objects.create(
            name='Заміна оливи',
            km_interval=15000
        )
        
        self.assertIn('Заміна оливи', str(rule))
        self.assertIn('15000', str(rule))


class FilterTypeModelTest(TestCase):
    """Tests for FilterType model"""
    
    def test_create_filter_type(self):
        """Test creating a filter type"""
        filter_type = FilterType.objects.create(
            name='Масляний фільтр',
            euro_standard='EURO5',
            replacement_interval_km=15000
        )
        
        self.assertEqual(filter_type.name, 'Масляний фільтр')
        self.assertEqual(filter_type.euro_standard, 'EURO5')
    
    def test_filter_type_str_with_euro(self):
        """Test string representation with euro standard"""
        filter_type = FilterType.objects.create(
            name='Паливний фільтр',
            euro_standard='EURO6',
            replacement_interval_km=30000
        )
        
        self.assertIn('Паливний фільтр', str(filter_type))
        self.assertIn('Євро-6', str(filter_type))
    
    def test_filter_type_str_without_euro(self):
        """Test string representation without euro standard"""
        filter_type = FilterType.objects.create(
            name='Повітряний фільтр',
            replacement_interval_km=20000
        )
        
        self.assertEqual(str(filter_type), 'Повітряний фільтр')


class MaintenanceKitModelTest(TestCase):
    """Tests for MaintenanceKit model - maintenance kit per vehicle"""
    
    def setUp(self):
        self.client = Client.objects.create(name='Test Client')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )
        self.oil = Part.objects.create(
            name='Моторна олива 10W-40',
            sku_code='OIL-10W40',
            selling_price=Decimal('800.00')
        )
    
    def test_create_maintenance_kit(self):
        """Test creating a maintenance kit"""
        kit = MaintenanceKit.objects.create(
            truck=self.truck,
            oil=self.oil,
            oil_quantity=Decimal('7.5'),
            oil_replacement_interval=15000
        )
        
        self.assertEqual(kit.truck, self.truck)
        self.assertEqual(kit.oil, self.oil)
        self.assertEqual(kit.oil_quantity, Decimal('7.5'))
    
    def test_maintenance_kit_str_representation(self):
        """Test string representation includes VIN and plate"""
        kit = MaintenanceKit.objects.create(
            truck=self.truck,
            oil=self.oil,
            oil_quantity=Decimal('7.5')
        )
        
        self.assertIn('1234567', str(kit))  # Last 7 VIN
        self.assertIn('AA1234BB', str(kit))


class MaintenanceKitFilterModelTest(TestCase):
    """Tests for MaintenanceKitFilter model"""
    
    def setUp(self):
        self.client = Client.objects.create(name='Test Client')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )
        self.oil = Part.objects.create(
            name='Моторна олива',
            sku_code='OIL-001',
            selling_price=Decimal('800.00')
        )
        self.filter_part = Part.objects.create(
            name='Фільтр оливи OEM',
            sku_code='FILTER-001',
            selling_price=Decimal('250.00')
        )
        self.filter_type = FilterType.objects.create(
            name='Масляний фільтр',
            replacement_interval_km=15000
        )
        self.kit = MaintenanceKit.objects.create(
            truck=self.truck,
            oil=self.oil,
            oil_quantity=Decimal('7.5')
        )
    
    def test_create_kit_filter(self):
        """Test adding a filter to maintenance kit"""
        kit_filter = MaintenanceKitFilter.objects.create(
            maintenance_kit=self.kit,
            filter_type=self.filter_type,
            part=self.filter_part,
            quantity=1
        )
        
        self.assertEqual(kit_filter.maintenance_kit, self.kit)
        self.assertEqual(kit_filter.filter_type, self.filter_type)
        self.assertEqual(kit_filter.quantity, 1)
    
    def test_kit_filter_custom_interval(self):
        """Test custom replacement interval overrides filter type default"""
        kit_filter = MaintenanceKitFilter.objects.create(
            maintenance_kit=self.kit,
            filter_type=self.filter_type,
            part=self.filter_part,
            quantity=1,
            custom_interval_km=10000
        )
        
        self.assertEqual(kit_filter.replacement_interval, 10000)
    
    def test_kit_filter_default_interval(self):
        """Test default interval from filter type is used"""
        kit_filter = MaintenanceKitFilter.objects.create(
            maintenance_kit=self.kit,
            filter_type=self.filter_type,
            part=self.filter_part,
            quantity=1
        )
        
        self.assertEqual(kit_filter.replacement_interval, 15000)
        