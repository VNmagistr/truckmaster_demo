"""
Pytest fixtures for the CRM project tests
"""
import pytest
from django.contrib.auth.models import User
from decimal import Decimal

from clients.models import Client, IvecoBaseModel, Truck
from inventory.models import Product
from orders.models import Employee, WorkGroup, WorkPrice, ServiceOrder


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='testpass123'
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='testpass123'
    )


@pytest.fixture
def client_obj(db):
    return Client.objects.create(
        name='Test Transport LLC',
        phone='+380501234567',
        email='test@transport.com'
    )


@pytest.fixture
def base_model(db):
    return IvecoBaseModel.objects.create(name='Daily')


@pytest.fixture
def truck(db, client_obj, base_model):
    return Truck.objects.create(
        client=client_obj,
        base_model=base_model,
        specific_model_name='35C15',
        full_vin='ZCFC35A0001234567',
        license_plate='AA1234BB',
        euro_standard='EURO5'
    )


@pytest.fixture
def employee(db):
    return Employee.objects.create(
        name='Іван Механік',
        position='Механік'
    )


@pytest.fixture
def work_group(db):
    return WorkGroup.objects.create(
        name='Двигун',
        hourly_rate=Decimal('600.00')
    )


@pytest.fixture
def work_price(db, work_group):
    return WorkPrice.objects.create(
        work_group=work_group,
        name='Заміна оливи',
        standard_hours=Decimal('1.5'),
        price=Decimal('0')
    )


@pytest.fixture
def service_order(db, client_obj, truck):
    return ServiceOrder.objects.create(
        order_number='ORD-TEST-001',
        client=client_obj,
        truck=truck,
        status='OPEN'
    )


@pytest.fixture
def oil_part(db):
    return Product.objects.create(
        name='Моторна олива 10W-40',
        sku_code='OIL-10W40',
        unit='l',
        cost_price=Decimal('500.00'),
        selling_price=Decimal('800.00'),
        current_stock=50
    )


@pytest.fixture
def filter_part(db):
    return Product.objects.create(
        name='Фільтр оливи',
        sku_code='FILTER-OIL-001',
        cost_price=Decimal('150.00'),
        selling_price=Decimal('250.00'),
        current_stock=20
    )


@pytest.fixture
def api_client(db, regular_user):
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=regular_user)
    return client
