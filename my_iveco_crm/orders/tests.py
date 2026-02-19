"""
Tests for orders app - models, business logic, price calculations
"""
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal

from .models import (
    WorkGroup, WorkPrice, ServiceOrder, ServiceWork,
    RepairPhoto, MaintenanceRule, MaintenanceLog,
    FilterType, MaintenanceKit, MaintenanceKitFilter
)
from clients.models import Client, IvecoBaseModel, Truck
from inventory.models import Product, UsedPart


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
        """Test string representation"""
        group = WorkGroup.objects.create(name='Двигун', hourly_rate=Decimal('600'))
        self.assertEqual(str(group), 'Двигун')

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

        self.assertEqual(str(work), 'Заміна оливи')


class ServiceOrderModelTest(TestCase):
    """Tests for ServiceOrder model"""

    def setUp(self):
        self.client_obj = Client.objects.create(name='Test Transport LLC')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client_obj,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )

    def test_create_service_order(self):
        """Test creating a service order"""
        order = ServiceOrder.objects.create(
            order_number='ORD-2024-001',
            client=self.client_obj,
            truck=self.truck,
            problem_description='Стук в двигуні'
        )

        self.assertEqual(order.order_number, 'ORD-2024-001')
        self.assertEqual(order.client, self.client_obj)
        self.assertEqual(order.truck, self.truck)
        self.assertEqual(order.status, ServiceOrder.StatusChoices.OPEN)

    def test_service_order_default_status(self):
        """Test default status is OPEN"""
        order = ServiceOrder.objects.create(client=self.client_obj, truck=self.truck)
        self.assertEqual(order.status, 'OPEN')

    def test_service_order_status_choices(self):
        """Test all status choices work"""
        statuses = ['OPEN', 'IN_PROGRESS', 'CLOSED', 'CANCELED']

        for i, status in enumerate(statuses):
            order = ServiceOrder.objects.create(
                order_number=f'ORD-{i}',
                client=self.client_obj,
                truck=self.truck,
                status=status
            )
            self.assertEqual(order.status, status)

    def test_service_order_str_representation(self):
        """Test string representation"""
        order = ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.client_obj,
            truck=self.truck
        )

        self.assertEqual(str(order), '№ORD-001')

    def test_service_order_ordering(self):
        """Test orders are ordered by created_at descending"""
        order1 = ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.client_obj,
            truck=self.truck
        )
        order2 = ServiceOrder.objects.create(
            order_number='ORD-002',
            client=self.client_obj,
            truck=self.truck
        )

        orders = list(ServiceOrder.objects.all())
        # Newest first
        self.assertEqual(orders[0], order2)
        self.assertEqual(orders[1], order1)


class ServiceOrderTotalCostTest(TestCase):
    """Tests for ServiceOrder.update_total_cost() method"""

    def setUp(self):
        self.client_obj = Client.objects.create(name='Test Client')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client_obj,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )

        self.mechanic = User.objects.create_user(username='mechanic', password='testpass123')
        self.work_group = WorkGroup.objects.create(name='Engine', hourly_rate=Decimal('500'))

        self.work_price = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Oil Change',
            standard_hours=Decimal('1.0')
        )

        self.part = Product.objects.create(
            name='Oil Filter',
            sku_code='OIL-001',
            selling_price=Decimal('200.00')
        )

        self.service_order = ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.client_obj,
            truck=self.truck
        )

    def test_update_total_cost_with_work_only(self):
        """Test total cost calculation with only work (no parts)"""
        ServiceWork.objects.create(
            service_order=self.service_order,
            work=self.work_price,
            mechanic=self.mechanic,
            hours_spent=Decimal('2.0')
        )

        self.service_order.refresh_from_db()

        # Work: price_at_moment (auto-filled from work_price: 1.0 * 500 = 500) × hours_spent (2.0) = 1000
        self.assertEqual(self.service_order.total_cost, Decimal('1000.00'))

    def test_update_total_cost_empty_order(self):
        """Test total cost for order without works"""
        self.service_order.update_total_cost()
        self.service_order.refresh_from_db()
        self.assertEqual(self.service_order.total_cost, Decimal('0'))


class ServiceWorkModelTest(TestCase):
    """Tests for ServiceWork model"""

    def setUp(self):
        self.client_obj = Client.objects.create(name='Test Client')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client_obj,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )
        self.mechanic = User.objects.create_user(username='mechanic', password='testpass123')
        self.work_group = WorkGroup.objects.create(name='Engine', hourly_rate=Decimal('500'))
        self.work_price = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Oil Change',
            standard_hours=Decimal('1.0')
        )
        self.service_order = ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.client_obj,
            truck=self.truck
        )

    def test_create_service_work(self):
        """Test creating a service work record"""
        work = ServiceWork.objects.create(
            service_order=self.service_order,
            work=self.work_price,
            mechanic=self.mechanic,
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
            mechanic=self.mechanic
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

        self.assertEqual(str(rule), 'Заміна оливи')


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

    def test_filter_type_str(self):
        """Test string representation"""
        filter_type = FilterType.objects.create(
            name='Паливний фільтр',
            euro_standard='EURO6',
            replacement_interval_km=30000
        )

        self.assertEqual(str(filter_type), 'Паливний фільтр')

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
        self.client_obj = Client.objects.create(name='Test Client')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client_obj,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )
        self.oil = Product.objects.create(
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
        )

        self.assertEqual(kit.truck, self.truck)
        self.assertEqual(kit.oil, self.oil)
        self.assertEqual(kit.oil_quantity, Decimal('7.5'))


class MaintenanceKitFilterModelTest(TestCase):
    """Tests for MaintenanceKitFilter model"""

    def setUp(self):
        self.client_obj = Client.objects.create(name='Test Client')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client_obj,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )
        self.oil = Product.objects.create(
            name='Моторна олива',
            sku_code='OIL-001',
            selling_price=Decimal('800.00')
        )
        self.filter_part = Product.objects.create(
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

    def test_kit_filter_default_quantity(self):
        """Test default quantity is 1"""
        kit_filter = MaintenanceKitFilter.objects.create(
            maintenance_kit=self.kit,
            filter_type=self.filter_type,
            part=self.filter_part,
        )

        self.assertEqual(kit_filter.quantity, 1)
