"""
Tests for API endpoints - DRF ViewSets
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal

from orders.models import (
    WorkGroup, WorkPrice, ServiceOrder, ServiceWork,
    MaintenanceRule, MaintenanceLog
)
from clients.models import Client, IvecoBaseModel, Truck
from inventory.models import Product


class APIAuthenticationTest(APITestCase):
    """Test API authentication requirements"""

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied"""
        response = self.client.get('/api/service-orders/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_access_allowed(self):
        """Test that authenticated requests are allowed"""
        user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=user)

        response = self.client.get('/api/service-orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ServiceOrderAPITest(APITestCase):
    """Tests for ServiceOrder API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)

        self.test_client = Client.objects.create(name='Test Transport LLC')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.test_client,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )

    def test_list_service_orders(self):
        """Test listing service orders"""
        ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.test_client,
            truck=self.truck
        )
        ServiceOrder.objects.create(
            order_number='ORD-002',
            client=self.test_client,
            truck=self.truck
        )

        response = self.client.get('/api/service-orders/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_service_order(self):
        """Test creating a service order via API"""
        data = {
            'order_number': 'ORD-NEW-001',
            'client': self.test_client.id,
            'truck': self.truck.id,
            'status': 'OPEN',
            'problem_description': 'Engine noise'
        }

        response = self.client.post('/api/service-orders/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ServiceOrder.objects.count(), 1)
        self.assertEqual(ServiceOrder.objects.first().order_number, 'ORD-NEW-001')

    def test_retrieve_service_order(self):
        """Test retrieving a single service order"""
        order = ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.test_client,
            truck=self.truck,
            problem_description='Test problem'
        )

        response = self.client.get(f'/api/service-orders/{order.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['order_number'], 'ORD-001')

    def test_update_service_order(self):
        """Test updating a service order"""
        order = ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.test_client,
            truck=self.truck,
            status='OPEN'
        )

        data = {
            'order_number': 'ORD-001',
            'client': self.test_client.id,
            'truck': self.truck.id,
            'status': 'IN_PROGRESS'
        }

        response = self.client.put(f'/api/service-orders/{order.id}/', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, 'IN_PROGRESS')

    def test_partial_update_service_order(self):
        """Test partial update (PATCH) of service order"""
        order = ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.test_client,
            truck=self.truck,
            status='OPEN'
        )

        response = self.client.patch(
            f'/api/service-orders/{order.id}/',
            {'status': 'CLOSED'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, 'CLOSED')

    def test_delete_service_order(self):
        """Test deleting a service order"""
        order = ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.test_client,
            truck=self.truck
        )

        response = self.client.delete(f'/api/service-orders/{order.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ServiceOrder.objects.count(), 0)


class WorkGroupAPITest(APITestCase):
    """Tests for WorkGroup API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)

    def test_list_work_groups(self):
        """Test listing work groups"""
        WorkGroup.objects.create(name='Engine', hourly_rate=Decimal('600'))
        WorkGroup.objects.create(name='Electrical', hourly_rate=Decimal('500'))

        response = self.client.get('/api/work-groups/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_work_group(self):
        """Test creating a work group"""
        data = {
            'name': 'Transmission',
            'hourly_rate': '700.00'
        }

        response = self.client.post('/api/work-groups/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WorkGroup.objects.first().hourly_rate, Decimal('700.00'))


class WorkPriceAPITest(APITestCase):
    """Tests for WorkPrice API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)

        self.work_group = WorkGroup.objects.create(name='Engine', hourly_rate=Decimal('500'))

    def test_list_work_prices(self):
        """Test listing work prices"""
        WorkPrice.objects.create(
            work_group=self.work_group,
            name='Oil Change',
            standard_hours=Decimal('1.0')
        )

        response = self.client.get('/api/work-prices/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_work_price(self):
        """Test creating a work price"""
        data = {
            'work_group': self.work_group.id,
            'name': 'New Work',
            'standard_hours': '2.0'
        }

        response = self.client.post('/api/work-prices/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ServiceWorkAPITest(APITestCase):
    """Tests for ServiceWork API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)

        self.test_client = Client.objects.create(name='Test Client')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.test_client,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )
        self.service_order = ServiceOrder.objects.create(
            order_number='ORD-001',
            client=self.test_client,
            truck=self.truck
        )
        self.mechanic = User.objects.create_user(username='mechanic', password='testpass123')
        self.work_group = WorkGroup.objects.create(name='Engine', hourly_rate=Decimal('500'))
        self.work_price = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Oil Change',
            standard_hours=Decimal('1.0')
        )

    def test_list_service_works(self):
        """Test listing service works"""
        ServiceWork.objects.create(
            service_order=self.service_order,
            work=self.work_price,
            mechanic=self.mechanic,
            hours_spent=Decimal('1.0')
        )

        response = self.client.get('/api/service-works/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_service_work(self):
        """Test creating a service work"""
        data = {
            'service_order': self.service_order.id,
            'work': self.work_price.id,
            'mechanic': self.mechanic.id,
            'hours_spent': '1.5',
            'description': 'Test work description'
        }

        response = self.client.post('/api/service-works/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ServiceWork.objects.count(), 1)


class MaintenanceRuleAPITest(APITestCase):
    """Tests for MaintenanceRule API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.base_model = IvecoBaseModel.objects.create(name='Daily')

    def test_list_maintenance_rules(self):
        """Test listing maintenance rules"""
        rule = MaintenanceRule.objects.create(
            name='Oil Change',
            km_interval=15000
        )
        rule.applicable_models.add(self.base_model)

        response = self.client.get('/api/maintenance-rules/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_maintenance_rule(self):
        """Test creating a maintenance rule"""
        data = {
            'name': 'Filter Replacement',
            'km_interval': 30000,
            'applicable_models': [self.base_model.id]
        }

        response = self.client.post('/api/maintenance-rules/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class MaintenanceLogAPITest(APITestCase):
    """Tests for MaintenanceLog API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)

        self.test_client = Client.objects.create(name='Test Client')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.test_client,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )
        self.rule = MaintenanceRule.objects.create(
            name='Oil Change',
            km_interval=15000
        )
        self.rule.applicable_models.add(self.base_model)

    def test_list_maintenance_logs(self):
        """Test listing maintenance logs"""
        MaintenanceLog.objects.create(
            truck=self.truck,
            rule=self.rule,
            date_performed='2024-01-15'
        )

        response = self.client.get('/api/maintenance-logs/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_maintenance_log(self):
        """Test creating a maintenance log"""
        data = {
            'truck': self.truck.id,
            'rule': self.rule.id,
            'date_performed': '2024-06-01',
        }

        response = self.client.post('/api/maintenance-logs/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
