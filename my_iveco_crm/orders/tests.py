"""
Tests for orders app - models, business logic, price calculations
"""
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from freezegun import freeze_time

from .models import (
    WorkGroup, WorkPrice, ServiceOrder, ServiceWork,
    RepairPhoto, MaintenanceRule, MaintenanceLog,
    MaintenanceKit, MaintenanceKitFilter, OrderStatusHistory,
    TruckMaintenanceIntervals,
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

        orders = list(ServiceOrder.objects.order_by('-id'))
        # Newest first (by id as fallback when timestamps are equal in tests)
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

    def test_update_total_cost_with_direct_parts_only(self):
        """Test total cost with parts added directly to order (no service work)"""
        from inventory.models import UsedPart
        UsedPart.objects.create(
            service_order=self.service_order,
            part=self.part,
            quantity=Decimal('3'),
            unit_price=Decimal('200.00'),
        )

        self.service_order.update_total_cost()
        self.service_order.refresh_from_db()

        # 3 × 200 = 600
        self.assertEqual(self.service_order.total_cost, Decimal('600.00'))

    def test_update_total_cost_with_parts_via_service_work(self):
        """Test total cost with parts attached to a service work"""
        from inventory.models import UsedPart
        work = ServiceWork.objects.create(
            service_order=self.service_order,
            work=self.work_price,
            mechanic=self.mechanic,
            hours_spent=Decimal('1.0'),
        )
        UsedPart.objects.create(
            service_work=work,
            service_order=self.service_order,
            part=self.part,
            quantity=Decimal('2'),
            unit_price=Decimal('200.00'),
        )

        self.service_order.refresh_from_db()

        # Work: 500 × 1.0 = 500; parts via work: 2 × 200 = 400 → total 900
        self.assertEqual(self.service_order.total_cost, Decimal('900.00'))

    def test_update_total_cost_combined(self):
        """Test total cost: work + parts via work + direct parts"""
        from inventory.models import UsedPart
        work = ServiceWork.objects.create(
            service_order=self.service_order,
            work=self.work_price,
            mechanic=self.mechanic,
            hours_spent=Decimal('2.0'),
        )
        # Part via service work
        UsedPart.objects.create(
            service_work=work,
            service_order=self.service_order,
            part=self.part,
            quantity=Decimal('1'),
            unit_price=Decimal('200.00'),
        )
        # Direct part
        extra_part = Product.objects.create(
            name='Air Filter',
            sku_code='AIR-001',
            selling_price=Decimal('150.00'),
        )
        UsedPart.objects.create(
            service_order=self.service_order,
            part=extra_part,
            quantity=Decimal('2'),
            unit_price=Decimal('150.00'),
        )

        self.service_order.update_total_cost()
        self.service_order.refresh_from_db()

        # Work: 500 × 2.0 = 1000; part via work: 1 × 200 = 200; direct: 2 × 150 = 300 → total 1500
        self.assertEqual(self.service_order.total_cost, Decimal('1500.00'))


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
        self.kit = MaintenanceKit.objects.create(
            truck=self.truck,
            oil=self.oil,
            oil_quantity=Decimal('7.5')
        )

    def test_create_kit_filter(self):
        """Test adding a filter to maintenance kit"""
        kit_filter = MaintenanceKitFilter.objects.create(
            maintenance_kit=self.kit,
            part=self.filter_part,
            quantity=1
        )

        self.assertEqual(kit_filter.maintenance_kit, self.kit)
        self.assertEqual(kit_filter.quantity, 1)

    def test_kit_filter_default_quantity(self):
        """Test default quantity is 1"""
        kit_filter = MaintenanceKitFilter.objects.create(
            maintenance_kit=self.kit,
            part=self.filter_part,
        )

        self.assertEqual(kit_filter.quantity, 1)


class AutoCloseDoneOrdersTaskTest(TestCase):
    """Tests for auto_close_done_orders Celery task"""

    NOW = "2025-06-15 12:00:00"

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

    def _make_done_order(self, order_number, done_at, intervals_snapshot=None):
        """Create a DONE order whose status history entry has changed_at=done_at."""
        with freeze_time(done_at):
            order = ServiceOrder.objects.create(
                order_number=order_number,
                client=self.client_obj,
                truck=self.truck,
                status=ServiceOrder.StatusChoices.DONE,
                intervals_snapshot=intervals_snapshot,
            )
            OrderStatusHistory.objects.create(
                order=order,
                from_status=ServiceOrder.StatusChoices.IN_PROGRESS,
                to_status=ServiceOrder.StatusChoices.DONE,
            )
        return order

    @freeze_time(NOW)
    def test_closes_order_older_than_one_week(self):
        """Order in DONE for >7 days must be closed."""
        from .tasks import auto_close_done_orders
        order = self._make_done_order('ORD-001', timezone.now() - timedelta(days=8))

        result = auto_close_done_orders()

        order.refresh_from_db()
        self.assertEqual(order.status, ServiceOrder.StatusChoices.CLOSED)
        self.assertEqual(result, 1)

    @freeze_time(NOW)
    def test_does_not_close_order_within_one_week(self):
        """Order in DONE for <7 days must stay DONE."""
        from .tasks import auto_close_done_orders
        order = self._make_done_order('ORD-001', timezone.now() - timedelta(days=6))

        result = auto_close_done_orders()

        order.refresh_from_db()
        self.assertEqual(order.status, ServiceOrder.StatusChoices.DONE)
        self.assertEqual(result, 0)

    @freeze_time(NOW)
    def test_does_not_close_order_at_exactly_one_week(self):
        """Order in DONE for exactly 7 days is NOT closed (strictly less-than threshold)."""
        from .tasks import auto_close_done_orders
        order = self._make_done_order('ORD-001', timezone.now() - timedelta(weeks=1))

        result = auto_close_done_orders()

        order.refresh_from_db()
        self.assertEqual(order.status, ServiceOrder.StatusChoices.DONE)
        self.assertEqual(result, 0)

    @freeze_time(NOW)
    def test_clears_intervals_snapshot_on_close(self):
        """intervals_snapshot must be set to None when the order is auto-closed."""
        from .tasks import auto_close_done_orders
        snapshot = {'engine_oil_last_km': 120000}
        order = self._make_done_order('ORD-001', timezone.now() - timedelta(days=8),
                                      intervals_snapshot=snapshot)

        auto_close_done_orders()

        order.refresh_from_db()
        self.assertIsNone(order.intervals_snapshot)

    @freeze_time(NOW)
    def test_does_not_close_marked_for_deletion(self):
        """Orders with marked_for_deletion=True must be skipped."""
        from .tasks import auto_close_done_orders
        order = self._make_done_order('ORD-001', timezone.now() - timedelta(days=8))
        order.marked_for_deletion = True
        order.save(update_fields=['marked_for_deletion'])

        result = auto_close_done_orders()

        order.refresh_from_db()
        self.assertEqual(order.status, ServiceOrder.StatusChoices.DONE)
        self.assertEqual(result, 0)

    @freeze_time(NOW)
    def test_does_not_touch_non_done_orders(self):
        """Orders with status OPEN or IN_PROGRESS must not be affected."""
        from .tasks import auto_close_done_orders
        open_order = ServiceOrder.objects.create(
            order_number='ORD-OPEN',
            client=self.client_obj,
            truck=self.truck,
            status=ServiceOrder.StatusChoices.OPEN,
        )
        in_progress_order = ServiceOrder.objects.create(
            order_number='ORD-IP',
            client=self.client_obj,
            truck=self.truck,
            status=ServiceOrder.StatusChoices.IN_PROGRESS,
        )

        result = auto_close_done_orders()

        open_order.refresh_from_db()
        in_progress_order.refresh_from_db()
        self.assertEqual(open_order.status, ServiceOrder.StatusChoices.OPEN)
        self.assertEqual(in_progress_order.status, ServiceOrder.StatusChoices.IN_PROGRESS)
        self.assertEqual(result, 0)

    @freeze_time(NOW)
    def test_order_without_done_history_is_not_closed(self):
        """DONE order with no status history entry must not be closed (last_done is None)."""
        from .tasks import auto_close_done_orders
        order = ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.client_obj,
            truck=self.truck,
            status=ServiceOrder.StatusChoices.DONE,
        )
        # No OrderStatusHistory created intentionally

        result = auto_close_done_orders()

        order.refresh_from_db()
        self.assertEqual(order.status, ServiceOrder.StatusChoices.DONE)
        self.assertEqual(result, 0)

    @freeze_time(NOW)
    def test_returns_correct_count_for_multiple_orders(self):
        """Return value must equal the number of actually closed orders."""
        from .tasks import auto_close_done_orders
        # 2 old orders → will be closed
        self._make_done_order('ORD-001', timezone.now() - timedelta(days=10))
        self._make_done_order('ORD-002', timezone.now() - timedelta(days=8))
        # 1 recent order → stays DONE
        self._make_done_order('ORD-003', timezone.now() - timedelta(days=3))

        result = auto_close_done_orders()

        self.assertEqual(result, 2)


class ServiceOrderSignalsTest(TestCase):
    """Tests for signals: OrderStatusHistory, TruckMaintenanceIntervals update/revert."""

    def setUp(self):
        self.client_obj = Client.objects.create(name='Test Transport LLC')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client_obj,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB',
        )
        self.mechanic = User.objects.create_user(username='mechanic', password='pass')
        self.work_group = WorkGroup.objects.create(name='ТО', hourly_rate=Decimal('500'))
        # Work name contains 'заміна оливи' → matches both TO_KEYWORDS and ENGINE_KW
        self.oil_work = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Заміна оливи двигуна',
            standard_hours=Decimal('1.0'),
        )
        self.gearbox_work = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Заміна оливи КПП',
            standard_hours=Decimal('1.0'),
        )

    def _make_order(self, **kwargs):
        return ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.client_obj,
            truck=self.truck,
            **kwargs,
        )

    # ── OrderStatusHistory ──────────────────────────────────────────────────

    def test_history_created_on_order_creation(self):
        """Creating an order must produce one history record with the initial status."""
        order = self._make_order()
        history = order.status_history.all()
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().to_status, ServiceOrder.StatusChoices.OPEN)
        self.assertEqual(history.first().from_status, '')

    def test_history_recorded_on_status_change(self):
        """Changing status must append a new history record."""
        order = self._make_order()
        order.status = ServiceOrder.StatusChoices.IN_PROGRESS
        order.save(update_fields=['status'])

        self.assertEqual(order.status_history.count(), 2)
        last = order.status_history.order_by('-changed_at').first()
        self.assertEqual(last.from_status, ServiceOrder.StatusChoices.OPEN)
        self.assertEqual(last.to_status, ServiceOrder.StatusChoices.IN_PROGRESS)

    def test_history_not_recorded_when_status_unchanged(self):
        """Saving without changing status must not append a history record."""
        order = self._make_order()
        order.problem_description = 'Updated description'
        order.save()

        self.assertEqual(order.status_history.count(), 1)

    # ── _update_maintenance_intervals ───────────────────────────────────────

    def test_done_transition_updates_engine_oil_last_km(self):
        """Transitioning to DONE with oil-change work updates engine_oil_last_km."""
        order = self._make_order(current_mileage=150000)
        ServiceWork.objects.create(
            service_order=order, work=self.oil_work, mechanic=self.mechanic,
        )

        order.status = ServiceOrder.StatusChoices.DONE
        order.save(update_fields=['status'])

        intervals = TruckMaintenanceIntervals.objects.get(truck=self.truck)
        self.assertEqual(intervals.engine_oil_last_km, 150000)

    def test_done_transition_updates_gearbox_oil_last_km(self):
        """Transitioning to DONE with gearbox-oil work updates gearbox_oil_last_km."""
        order = self._make_order(current_mileage=200000)
        ServiceWork.objects.create(
            service_order=order, work=self.gearbox_work, mechanic=self.mechanic,
        )

        order.status = ServiceOrder.StatusChoices.DONE
        order.save(update_fields=['status'])

        intervals = TruckMaintenanceIntervals.objects.get(truck=self.truck)
        self.assertEqual(intervals.gearbox_oil_last_km, 200000)

    def test_done_transition_saves_snapshot_on_order(self):
        """intervals_snapshot must be saved on the order before updating intervals."""
        TruckMaintenanceIntervals.objects.create(truck=self.truck, engine_oil_last_km=100000)
        order = self._make_order(current_mileage=115000)
        ServiceWork.objects.create(
            service_order=order, work=self.oil_work, mechanic=self.mechanic,
        )

        order.status = ServiceOrder.StatusChoices.DONE
        order.save(update_fields=['status'])

        order.refresh_from_db()
        self.assertIsNotNone(order.intervals_snapshot)
        self.assertEqual(order.intervals_snapshot['engine_oil_last_km'], 100000)

    def test_done_transition_without_mileage_skips_intervals(self):
        """If current_mileage is not set, intervals must not be touched."""
        order = self._make_order(current_mileage=None)
        ServiceWork.objects.create(
            service_order=order, work=self.oil_work, mechanic=self.mechanic,
        )

        order.status = ServiceOrder.StatusChoices.DONE
        order.save(update_fields=['status'])

        self.assertFalse(TruckMaintenanceIntervals.objects.filter(truck=self.truck).exists())

    def test_done_transition_without_maintenance_work_skips_intervals(self):
        """If no maintenance work in the order, intervals must not be touched."""
        regular_work = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Заміна гальмівних колодок',
            standard_hours=Decimal('1.0'),
        )
        order = self._make_order(current_mileage=120000)
        ServiceWork.objects.create(
            service_order=order, work=regular_work, mechanic=self.mechanic,
        )

        order.status = ServiceOrder.StatusChoices.DONE
        order.save(update_fields=['status'])

        self.assertFalse(TruckMaintenanceIntervals.objects.filter(truck=self.truck).exists())

    # ── _revert_maintenance_intervals ───────────────────────────────────────

    def test_revert_from_done_to_open_restores_intervals(self):
        """Reverting DONE→OPEN must restore engine_oil_last_km from snapshot."""
        TruckMaintenanceIntervals.objects.create(truck=self.truck, engine_oil_last_km=100000)
        order = self._make_order(current_mileage=115000)
        ServiceWork.objects.create(
            service_order=order, work=self.oil_work, mechanic=self.mechanic,
        )

        # Transition to DONE — updates intervals to 115000, snapshot = {100000}
        order.status = ServiceOrder.StatusChoices.DONE
        order.save(update_fields=['status'])

        intervals = TruckMaintenanceIntervals.objects.get(truck=self.truck)
        self.assertEqual(intervals.engine_oil_last_km, 115000)

        # Revert to OPEN — must restore 100000
        order.status = ServiceOrder.StatusChoices.OPEN
        order.save(update_fields=['status'])

        intervals.refresh_from_db()
        self.assertEqual(intervals.engine_oil_last_km, 100000)

    def test_revert_clears_snapshot(self):
        """After reverting, intervals_snapshot must be cleared."""
        TruckMaintenanceIntervals.objects.create(truck=self.truck, engine_oil_last_km=100000)
        order = self._make_order(current_mileage=115000)
        ServiceWork.objects.create(
            service_order=order, work=self.oil_work, mechanic=self.mechanic,
        )

        order.status = ServiceOrder.StatusChoices.DONE
        order.save(update_fields=['status'])

        order.status = ServiceOrder.StatusChoices.OPEN
        order.save(update_fields=['status'])

        order.refresh_from_db()
        self.assertIsNone(order.intervals_snapshot)

    def test_snapshot_cleared_on_closed(self):
        """Moving to CLOSED must clear intervals_snapshot."""
        order = self._make_order(
            intervals_snapshot={'engine_oil_last_km': 100000},
        )
        order.status = ServiceOrder.StatusChoices.CLOSED
        order.save(update_fields=['status'])

        order.refresh_from_db()
        self.assertIsNone(order.intervals_snapshot)

    def test_snapshot_cleared_on_canceled(self):
        """Moving to CANCELED must clear intervals_snapshot."""
        order = self._make_order(
            intervals_snapshot={'engine_oil_last_km': 100000},
        )
        order.status = ServiceOrder.StatusChoices.CANCELED
        order.save(update_fields=['status'])

        order.refresh_from_db()
        self.assertIsNone(order.intervals_snapshot)
