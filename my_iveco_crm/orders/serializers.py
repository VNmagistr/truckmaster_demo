from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    ServiceOrder, ServiceWork, WorkGroup, WorkPrice, 
    RepairPhoto, MaintenanceRule, MaintenanceLog, MaintenanceKit
)
from clients.models import Client, Truck
from inventory.models import UsedPart

User = get_user_model()

class ClientSerializerForOrder(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'phone']

class TruckSerializerForOrder(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    client_id = serializers.SerializerMethodField()

    class Meta:
        model = Truck
        fields = ['id', 'license_plate', 'specific_model_name', 'last_seven_vin', 'client_id', 'client_name']

    def get_client_name(self, obj):
        client = getattr(obj, 'client', getattr(obj, 'owner', None))
        return client.name if client else None

    def get_client_id(self, obj):
        client = getattr(obj, 'client', getattr(obj, 'owner', None))
        return client.id if client else None

class MechanicSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name']
        
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

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
        fields = ['service_order', 'work', 'description', 'mechanic', 'hours_spent']

class RepairPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairPhoto
        fields = '__all__'

class ServiceOrderWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOrder
        fields = '__all__'

    def validate(self, data):
        truck = data.get('truck')
        client = data.get('client')

        if truck and not client:
            truck_client = getattr(truck, 'client', getattr(truck, 'owner', None))
            if truck_client:
                data['client'] = truck_client
        return data

class ServiceOrderListSerializer(serializers.ModelSerializer):
    client = ClientSerializerForOrder(read_only=True)
    truck = TruckSerializerForOrder(read_only=True)
    marked_for_deletion_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ServiceOrder
        fields = [
            'id', 'order_number', 'client', 'truck', 'status', 
            'total_cost', 'created_at', 'marked_for_deletion',
            'marked_for_deletion_by_name'
        ]

    def get_marked_for_deletion_by_name(self, obj):
        if obj.marked_for_deletion_by:
            u = obj.marked_for_deletion_by
            return f"{u.first_name} {u.last_name}".strip() or u.username
        return None

class ServiceOrderDetailSerializer(serializers.ModelSerializer): 
    client = ClientSerializerForOrder(read_only=True)
    truck = TruckSerializerForOrder(read_only=True)
    works = ServiceWorkSerializer(many=True, read_only=True)
    photos = RepairPhotoSerializer(many=True, read_only=True)
    marked_for_deletion_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ServiceOrder
        fields = [
            'id', 'order_number', 'client', 'truck', 'problem_description', 
            'current_mileage', 'status', 'created_at', 'updated_at', 
            'total_cost', 'car_photo', 'odometer_photo', 'dashboard_photo', 
            'works', 'photos', 'marked_for_deletion', 
            'marked_for_deletion_by', 'marked_for_deletion_by_name', 
            'marked_for_deletion_at', 'deletion_reason',
        ]
        
    def get_marked_for_deletion_by_name(self, obj):
        if obj.marked_for_deletion_by:
            u = obj.marked_for_deletion_by
            return f"{u.first_name} {u.last_name}".strip() or u.username
        return None

class MaintenanceRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRule
        fields = '__all__'

class MaintenanceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceLog
        fields = '__all__'

class MaintenanceKitSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceKit
        fields = '__all__'