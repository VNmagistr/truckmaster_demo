"""
Tests for clients app - models, admin functionality
"""
from django.test import TestCase, Client as TestClient
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal

from .models import Client, IvecoBaseModel, Truck, OwnershipHistory
from .admin import TruckAdmin



class ClientModelTest(TestCase):
    """Tests for Client model"""
    
    def setUp(self):
        self.client_data = {
            'name': 'Test Company LLC',
            'phone': '+380501234567',
            'email': 'test@example.com',
            'address': 'Kyiv, Test Street 1',
            'telegram_chat_id': 123456789
        }
    
    def test_create_client(self):
        """Test creating a client with all fields"""
        client = Client.objects.create(**self.client_data)
        
        self.assertEqual(client.name, 'Test Company LLC')
        self.assertEqual(client.phone, '+380501234567')
        self.assertEqual(client.email, 'test@example.com')
        self.assertEqual(client.telegram_chat_id, 123456789)
    
    def test_client_str_representation(self):
        """Test string representation of Client"""
        client = Client.objects.create(name='Test Client')
        self.assertEqual(str(client), 'Test Client')
    
    def test_client_ordering(self):
        """Test clients are ordered by name"""
        Client.objects.create(name='Zebra Company')
        Client.objects.create(name='Alpha Company')
        Client.objects.create(name='Beta Company')
        
        clients = list(Client.objects.all())
        self.assertEqual(clients[0].name, 'Alpha Company')
        self.assertEqual(clients[1].name, 'Beta Company')
        self.assertEqual(clients[2].name, 'Zebra Company')
    
    def test_client_phone_unique(self):
        """Test phone number uniqueness"""
        Client.objects.create(name='Client 1', phone='+380501111111')
        
        with self.assertRaises(Exception):
            Client.objects.create(name='Client 2', phone='+380501111111')
    
    def test_client_telegram_id_unique(self):
        """Test telegram_chat_id uniqueness"""
        Client.objects.create(name='Client 1', telegram_chat_id=111111)
        
        with self.assertRaises(Exception):
            Client.objects.create(name='Client 2', telegram_chat_id=111111)
    
    def test_client_optional_fields(self):
        """Test that optional fields can be null"""
        client = Client.objects.create(name='Minimal Client')
        
        self.assertIsNone(client.phone)
        self.assertIsNone(client.email)
        self.assertIsNone(client.address)
        self.assertIsNone(client.telegram_chat_id)


class IvecoBaseModelTest(TestCase):
    """Tests for IvecoBaseModel"""
    
    def test_create_base_model(self):
        """Test creating Iveco base model"""
        model = IvecoBaseModel.objects.create(name='Daily')
        
        self.assertEqual(model.name, 'Daily')
        self.assertEqual(str(model), 'Daily')
    
    def test_base_model_unique_name(self):
        """Test base model name uniqueness"""
        IvecoBaseModel.objects.create(name='Daily')
        
        with self.assertRaises(Exception):
            IvecoBaseModel.objects.create(name='Daily')
    
    def test_base_model_ordering(self):
        """Test base models are ordered by name"""
        IvecoBaseModel.objects.create(name='Stralis')
        IvecoBaseModel.objects.create(name='Daily')
        IvecoBaseModel.objects.create(name='Eurocargo')
        
        models = list(IvecoBaseModel.objects.all())
        self.assertEqual(models[0].name, 'Daily')
        self.assertEqual(models[1].name, 'Eurocargo')
        self.assertEqual(models[2].name, 'Stralis')


class TruckModelTest(TestCase):
    """Tests for Truck model"""
    
    def setUp(self):
        self.client = Client.objects.create(name='Test Transport')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
    
    def test_create_truck(self):
        """Test creating a truck"""
        truck = Truck.objects.create(
            client=self.client,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0005678901',
            license_plate='AA1234BB'
        )
        
        self.assertEqual(truck.specific_model_name, '35C15')
        self.assertEqual(truck.license_plate, 'AA1234BB')
        self.assertEqual(truck.client, self.client)
    
    def test_last_seven_vin_auto_generated(self):
        """Test that last_seven_vin is automatically generated from full_vin"""
        truck = Truck.objects.create(
            client=self.client,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0005678901',
            license_plate='AA1234BB'
        )
        
        self.assertEqual(truck.last_seven_vin, '5678901')
    
    def test_truck_str_representation(self):
        """Test string representation of Truck"""
        truck = Truck.objects.create(
            client=self.client,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0005678901',
            license_plate='AA1234BB',
            euro_standard='EURO5'
        )
        
        self.assertIn('35C15', str(truck))
        self.assertIn('AA1234BB', str(truck))
        self.assertIn('Євро-5', str(truck))
    
    def test_truck_euro_standard_choices(self):
        """Test euro standard choices"""
        truck = Truck.objects.create(
            client=self.client,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0005678901',
            license_plate='AA1234BB',
            euro_standard='EURO6'
        )
        
        self.assertEqual(truck.get_euro_standard_display(), 'Євро-6')
    
    def test_truck_vin_unique(self):
        """Test full_vin uniqueness"""
        Truck.objects.create(
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0005678901',
            license_plate='AA1111BB'
        )

        with self.assertRaises(Exception):
            Truck.objects.create(
                base_model=self.base_model,
                specific_model_name='35C15',
                full_vin='ZCFC35A0005678901',
                license_plate='AA2222BB'
            )

    def test_vin_exactly_17_chars_is_valid(self):
        """VIN with exactly 17 characters must pass validation."""
        from django.core.exceptions import ValidationError
        truck = Truck(
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0005678901',  # 17 chars
            license_plate='AA9999BB',
        )
        try:
            truck.full_clean()
        except ValidationError as e:
            if 'full_vin' in e.message_dict:
                self.fail(f"Valid 17-char VIN raised ValidationError: {e}")

    def test_vin_shorter_than_17_chars_is_invalid(self):
        """VIN shorter than 17 characters must fail validation."""
        from django.core.exceptions import ValidationError
        truck = Truck(
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A000567',  # 13 chars
            license_plate='AA9999BB',
        )
        with self.assertRaises(ValidationError) as ctx:
            truck.full_clean()
        self.assertIn('full_vin', ctx.exception.message_dict)

    def test_vin_longer_than_17_chars_is_invalid(self):
        """VIN longer than 17 characters must fail validation (max_length=17)."""
        from django.core.exceptions import ValidationError
        truck = Truck(
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A000567890123',  # 19 chars
            license_plate='AA9999BB',
        )
        with self.assertRaises(ValidationError) as ctx:
            truck.full_clean()
        self.assertIn('full_vin', ctx.exception.message_dict)


class OwnershipHistoryTest(TestCase):
    """Tests for OwnershipHistory - automatic tracking of ownership changes"""
    
    def setUp(self):
        self.client1 = Client.objects.create(name='First Owner')
        self.client2 = Client.objects.create(name='Second Owner')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        
        self.truck = Truck.objects.create(
            client=self.client1,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0005678901',
            license_plate='AA1234BB'
        )
    
    def test_ownership_history_created_on_client_change(self):
        """Test that history record is created when client changes"""
        # Initially no history
        self.assertEqual(OwnershipHistory.objects.count(), 0)
        
        # Change owner
        self.truck.client = self.client2
        self.truck.save()
        
        # History should be created
        self.assertEqual(OwnershipHistory.objects.count(), 1)
        
        history = OwnershipHistory.objects.first()
        self.assertEqual(history.truck, self.truck)
        self.assertEqual(history.client, self.client1)  # Previous owner
        self.assertEqual(history.license_plate, 'AA1234BB')
    
    def test_ownership_history_created_on_plate_change(self):
        """Test that history record is created when license plate changes"""
        self.truck.license_plate = 'BB5555CC'
        self.truck.save()
        
        self.assertEqual(OwnershipHistory.objects.count(), 1)
        
        history = OwnershipHistory.objects.first()
        self.assertEqual(history.license_plate, 'AA1234BB')  # Previous plate
    
    def test_no_history_on_other_field_change(self):
        """Test that history is NOT created when other fields change"""
        self.truck.euro_standard = 'EURO6'
        self.truck.save()
        
        self.assertEqual(OwnershipHistory.objects.count(), 0)
    
    def test_multiple_ownership_changes(self):
        """Test multiple ownership changes create multiple records"""
        client3 = Client.objects.create(name='Third Owner')
        
        # First change
        self.truck.client = self.client2
        self.truck.save()
        
        # Second change
        self.truck.client = client3
        self.truck.save()
        
        self.assertEqual(OwnershipHistory.objects.count(), 2)
        
        # Check ordering (newest first)
        histories = list(OwnershipHistory.objects.all())
        self.assertEqual(histories[0].client, self.client2)  # Most recent previous
        self.assertEqual(histories[1].client, self.client1)  # First previous


class TruckAdminFilterTest(TestCase):
    """Tests for TruckAdmin - filtering trucks by client in autocomplete"""
    
    def setUp(self):
        self.site = AdminSite()
        self.admin = TruckAdmin(Truck, self.site)
        
        self.client1 = Client.objects.create(name='Client One')
        self.client2 = Client.objects.create(name='Client Two')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        
        # Create trucks for different clients
        self.truck1 = Truck.objects.create(
            client=self.client1,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001111111',
            license_plate='AA1111AA'
        )
        self.truck2 = Truck.objects.create(
            client=self.client1,
            base_model=self.base_model,
            specific_model_name='35C18',
            full_vin='ZCFC35A0002222222',
            license_plate='AA2222AA'
        )
        self.truck3 = Truck.objects.create(
            client=self.client2,
            base_model=self.base_model,
            specific_model_name='50C15',
            full_vin='ZCFC35A0003333333',
            license_plate='BB3333BB'
        )
        
        # Create admin user
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
    
    def test_get_search_results_filters_by_client(self):
        """Test that get_search_results filters trucks by client_id"""
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/admin/clients/truck/autocomplete/', {'client_id': self.client1.id})
        request.user = self.admin_user
        
        queryset = Truck.objects.all()
        result_queryset, use_distinct = self.admin.get_search_results(request, queryset, '')
        
        # Should only return trucks for client1
        self.assertEqual(result_queryset.count(), 2)
        self.assertIn(self.truck1, result_queryset)
        self.assertIn(self.truck2, result_queryset)
        self.assertNotIn(self.truck3, result_queryset)
    
    def test_get_search_results_without_client_filter(self):
        """Test that without client_id all trucks are returned"""
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/admin/clients/truck/autocomplete/')
        request.user = self.admin_user
        
        queryset = Truck.objects.all()
        result_queryset, use_distinct = self.admin.get_search_results(request, queryset, '')
        
        # Should return all trucks
        self.assertEqual(result_queryset.count(), 3)
