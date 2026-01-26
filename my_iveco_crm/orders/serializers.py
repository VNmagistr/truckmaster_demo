from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    ServiceOrder, ServiceWork, WorkGroup, WorkPrice, 
    RepairPhoto, MaintenanceRule, MaintenanceLog
)
from clients.models import Client, Truck
from inventory.models import UsedPart

User = get_user_model()

# ----- Серіалізатори для Клієнтів та Вантажівок -----
class ClientSerializerForOrder(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'phone']

class TruckSerializerForOrder(serializers.ModelSerializer):
    # Додаємо дані клієнта, щоб фронтенд міг їх "підтягнути" автоматично
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_id = serializers.PrimaryKeyRelatedField(source='client', read_only=True)

    class Meta:
        model = Truck
        fields = ['id', 'license_plate', 'specific_model_name', 'last_seven_vin', 'client_id', 'client_name']

# ----- Серіалізатор для Механіка (User) -----
class MechanicSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name']
        
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

# ----- Серіалізатори для додатку Orders -----

class WorkGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkGroup
        fields = '__all__'

class WorkPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkPrice
        fields = '__all__'

class UsedPartSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsedPart
        fields = '__all__'

# --- Серіалізатори Виконаних Робіт (ServiceWork) ---

class ServiceWorkSerializer(serializers.ModelSerializer):
    work = WorkPriceSerializer(read_only=True)
    mechanic = MechanicSerializer(read_only=True)
    used_parts = UsedPartSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceWork
        fields = '__all__'

class ServiceWorkWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceWork
        fields = [
            'service_order', 
            'work', 
            'description', 
            'mechanic',
            'hours_spent'
        ]

class RepairPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairPhoto
        fields = '__all__'

# --- Серіалізатори Замовлень (ServiceOrder) ---

class ServiceOrderWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOrder
        fields = [
            'order_number', 
            'client',
            'truck',
            'problem_description',
            'current_mileage',  # <-- ПОВЕРНУЛИ ПРОБІГ
            'status',
            'car_photo',
            'odometer_photo',
            'dashboard_photo',
        ]

    def validate(self, data):
        """
        Автоматична бізнес-логіка:
        Якщо вказано Вантажівку, але не вказано Клієнта -> підтягуємо власника авто.
        """
        truck = data.get('truck')
        client = data.get('client')

        if truck and not client:
            if truck.client:
                data['client'] = truck.client
            else:
                raise serializers.ValidationError({"client": "У цієї вантажівки немає власника. Будь ласка, оберіть клієнта вручну."})
        
        return data

class ServiceOrderListSerializer(serializers.ModelSerializer):
    client = ClientSerializerForOrder(read_only=True)
    truck = TruckSerializerForOrder(read_only=True)

    class Meta:
        model = ServiceOrder
        fields = [
            'id', 
            'order_number', 
            'client', 
            'truck', 
            'status', 
            'created_at', 
            'problem_description',
            'marked_for_deletion',
        ]

class ServiceOrderDetailSerializer(serializers.ModelSerializer): 
    client = ClientSerializerForOrder(read_only=True)
    truck = TruckSerializerForOrder(read_only=True)
    works = ServiceWorkSerializer(many=True, read_only=True)
    photos = RepairPhotoSerializer(many=True, read_only=True)
    marked_for_deletion_by_name = serializers.CharField(
        source='marked_for_deletion_by.get_full_name',
        read_only=True
    )

    class Meta:
        model = ServiceOrder
        fields = [
            'id', 
            'order_number', 
            'client', 
            'truck', 
            'problem_description',
            'current_mileage',
            'status', 
            'created_at', 
            'updated_at',
            'total_cost',
            'car_photo',
            'odometer_photo',
            'dashboard_photo',
            'works', 
            'photos',
            'marked_for_deletion',
            'marked_for_deletion_by',
            'marked_for_deletion_by_name',
            'marked_for_deletion_at',
            'deletion_reason',
        ]

# --- Серіалізатори Регламентів ---

class MaintenanceRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRule
        fields = '__all__'

class MaintenanceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceLog
        fields = '__all__'