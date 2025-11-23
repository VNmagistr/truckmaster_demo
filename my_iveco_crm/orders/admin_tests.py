"""
Tests for Django Admin functionality
"""
from django.test import TestCase, RequestFactory, Client as TestClient
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal

from orders.models import (
    Employee, WorkGroup, WorkPrice, ServiceOrder, ServiceWork
)
from orders.admin import ServiceOrderAdmin
from clients.models import Client, IvecoBaseModel, Truck
from clients.admin import TruckAdmin
from inventory.models import Part, UsedPart


class ServiceOrderAdminTest(TestCase):
    """Tests for ServiceOrderAdmin functionality"""
    
    def setUp(self):
        self.site = AdminSite()
        self.admin = ServiceOrderAdmin(ServiceOrder, self.site)
        self.factory = RequestFactory()
        
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        
        self.client_obj = Client.objects.create(name='Test Transport LLC')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client_obj,
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
            client=self.client_obj,
            truck=self.truck
        )
    
    def test_admin_list_display(self):
        """Test admin list display fields"""
        expected_fields = ('order_number', 'client', 'truck', 'status', 'total_cost', 'created_at')
        self.assertEqual(self.admin.list_display, expected_fields)
    
    def test_admin_search_fields(self):
        """Test admin search fields"""
        self.assertIn('order_number', self.admin.search_fields)
        self.assertIn('client__name', self.admin.search_fields)
        self.assertIn('truck__license_plate', self.admin.search_fields)
    
    def test_get_all_parts_display_no_parts(self):
        """Test parts display when no parts added"""
        result = self.admin.get_all_parts_display(self.service_order)
        self.assertEqual(result, "Запчастини не додано")
    
    def test_get_all_parts_display_with_parts(self):
        """Test parts display with parts added"""
        service_work = ServiceWork.objects.create(
            service_order=self.service_order,
            work=self.work_price,
            employee=self.employee,
            hours_spent=Decimal('1.0')
        )
        
        part = Part.objects.create(
            name='Oil Filter',
            sku_code='OIL-001',
            selling_price=Decimal('200.00')
        )
        
        UsedPart.objects.create(
            service_work=service_work,
            part=part,
            quantity=2
        )
        
        result = self.admin.get_all_parts_display(self.service_order)
        
        self.assertIn('Oil Filter', result)
        self.assertIn('OIL-001', result)
        self.assertIn('2 шт.', result)
    
    def test_get_all_parts_display_oil_in_liters(self):
        """Test that oil is displayed in liters, not pieces"""
        service_work = ServiceWork.objects.create(
            service_order=self.service_order,
            work=self.work_price,
            employee=self.employee,
            hours_spent=Decimal('1.0')
        )
        
        oil = Part.objects.create(
            name='Моторна олива 10W-40',
            sku_code='OIL-10W40',
            selling_price=Decimal('800.00')
        )
        
        UsedPart.objects.create(
            service_work=service_work,
            part=oil,
            quantity=8
        )
        
        result = self.admin.get_all_parts_display(self.service_order)
        
        self.assertIn('8 л', result)
        self.assertNotIn('8 шт', result)
    
    def test_get_all_parts_display_oil_filter_in_pieces(self):
        """Test that oil FILTER is displayed in pieces, not liters"""
        service_work = ServiceWork.objects.create(
            service_order=self.service_order,
            work=self.work_price,
            employee=self.employee,
            hours_spent=Decimal('1.0')
        )
        
        oil_filter = Part.objects.create(
            name='Фільтр оливи',
            sku_code='FILTER-OIL-001',
            selling_price=Decimal('250.00')
        )
        
        UsedPart.objects.create(
            service_work=service_work,
            part=oil_filter,
            quantity=1
        )
        
        result = self.admin.get_all_parts_display(self.service_order)
        
        self.assertIn('1 шт.', result)
        self.assertNotIn('1 л', result)
    
    def test_get_all_parts_display_new_order(self):
        """Test parts display for unsaved order"""
        new_order = ServiceOrder(client=self.client_obj, truck=self.truck)
        # Don't save - pk is None
        
        result = self.admin.get_all_parts_display(new_order)
        self.assertEqual(result, "Спочатку збережіть замовлення")
    
    def test_get_trucks_by_client_endpoint(self):
        """Test the custom endpoint for getting trucks by client"""
        # Create another truck for a different client
        other_client = Client.objects.create(name='Other Client')
        other_truck = Truck.objects.create(
            client=other_client,
            base_model=self.base_model,
            specific_model_name='50C15',
            full_vin='ZCFC35A0009999999',
            license_plate='BB9999BB'
        )
        
        request = self.factory.get(
            '/admin/orders/serviceorder/get-trucks-by-client/',
            {'client_id': self.client_obj.id}
        )
        request.user = self.admin_user
        
        response = self.admin.get_trucks_by_client(request)
        
        import json
        data = json.loads(response.content)
        
        self.assertEqual(len(data['trucks']), 1)
        self.assertEqual(data['trucks'][0]['id'], self.truck.id)
    
    def test_get_trucks_by_client_no_client_id(self):
        """Test endpoint without client_id returns empty list"""
        request = self.factory.get('/admin/orders/serviceorder/get-trucks-by-client/')
        request.user = self.admin_user
        
        response = self.admin.get_trucks_by_client(request)
        
        import json
        data = json.loads(response.content)
        
        self.assertEqual(data['trucks'], [])


class TruckAdminFilterTest(TestCase):
    """Tests for TruckAdmin autocomplete filtering"""
    
    def setUp(self):
        self.site = AdminSite()
        self.admin = TruckAdmin(Truck, self.site)
        self.factory = RequestFactory()
        
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        
        self.client1 = Client.objects.create(name='Client One')
        self.client2 = Client.objects.create(name='Client Two')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        
        self.truck1 = Truck.objects.create(
            client=self.client1,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001111111',
            license_plate='AA1111AA'
        )
        self.truck2 = Truck.objects.create(
            client=self.client2,
            base_model=self.base_model,
            specific_model_name='50C15',
            full_vin='ZCFC35A0002222222',
            license_plate='BB2222BB'
        )
    
    def test_get_search_results_filters_by_client(self):
        """Test autocomplete filters trucks by client_id"""
        request = self.factory.get(
            '/admin/clients/truck/autocomplete/',
            {'client_id': self.client1.id, 'term': ''}
        )
        request.user = self.admin_user
        
        queryset = Truck.objects.all()
        result_queryset, use_distinct = self.admin.get_search_results(request, queryset, '')
        
        self.assertEqual(result_queryset.count(), 1)
        self.assertEqual(result_queryset.first(), self.truck1)
    
    def test_get_search_results_without_filter(self):
        """Test autocomplete returns all trucks without client_id"""
        request = self.factory.get(
            '/admin/clients/truck/autocomplete/',
            {'term': ''}
        )
        request.user = self.admin_user
        
        queryset = Truck.objects.all()
        result_queryset, use_distinct = self.admin.get_search_results(request, queryset, '')
        
        self.assertEqual(result_queryset.count(), 2)


class AdminAccessTest(TestCase):
    """Tests for admin access and permissions"""
    
    def setUp(self):
        self.client = TestClient()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123'
        )
    
    def test_admin_login_required(self):
        """Test that admin requires login"""
        response = self.client.get('/admin/')
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_admin_accessible_by_superuser(self):
        """Test that superuser can access admin"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get('/admin/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_admin_not_accessible_by_regular_user(self):
        """Test that regular user cannot access admin"""
        self.client.login(username='user', password='testpass123')
        
        response = self.client.get('/admin/')
        
        # Should redirect to login (no permission)
        self.assertEqual(response.status_code, 302)
    
    def test_service_order_admin_page(self):
        """Test service order admin changelist page loads"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get('/admin/orders/serviceorder/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_client_admin_page(self):
        """Test client admin changelist page loads"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get('/admin/clients/client/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_part_admin_page(self):
        """Test part admin changelist page loads"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get('/admin/inventory/part/')
        
        self.assertEqual(response.status_code, 200)


class WorkPriceAdminTest(TestCase):
    """Tests for WorkPriceAdmin - calculated price display"""
    
    def setUp(self):
        self.client = TestClient()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        
        self.work_group = WorkGroup.objects.create(
            name='Engine',
            hourly_rate=Decimal('600.00')
        )
        self.work_price = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Oil Change',
            standard_hours=Decimal('1.5')
        )
    
    def test_work_price_list_shows_calculated_price(self):
        """Test that work price list shows calculated price"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get('/admin/orders/workprice/')
        
        self.assertEqual(response.status_code, 200)
        # 1.5 hours × 600 грн = 900 грн
        self.assertContains(response, '900')
