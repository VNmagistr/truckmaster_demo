# orders/serializers.py

from rest_framework import serializers
from .models import ServiceOrder, ServiceWork, RepairPhoto, MaintenanceRule, MaintenanceLog


class ClientSerializerForOrder(serializers.Serializer):
    """Мінімальна інформація про клієнта для відображення в замовленнях"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    last_name = serializers.CharField(allow_blank=True, allow_null=True)
    phone = serializers.CharField(allow_blank=True, allow_null=True)


class TruckSerializerForOrder(serializers.Serializer):
    """Мінімальна інформація про вантажівку для відображення в замовленнях"""
    id = serializers.IntegerField()
    license_plate = serializers.CharField()
    specific_model_name = serializers.CharField()
    last_seven_vin = serializers.CharField(allow_blank=True, allow_null=True)


class ServiceWorkSerializer(serializers.ModelSerializer):
    """Серіалізатор для робіт у замовленні"""
    work_name = serializers.CharField(source='work.name', read_only=True, allow_null=True)
    work_group_name = serializers.CharField(source='work.work_group.name', read_only=True, allow_null=True)
    
    class Meta:
        model = ServiceWork
        fields = [
            'id',
            'service_order',
            'work',
            'work_name',
            'work_group_name',
            'description',
            'hours_spent',
            'hourly_rate',
            'total_cost',
            'created_at'
        ]
        read_only_fields = ['total_cost', 'created_at']


class RepairPhotoSerializer(serializers.ModelSerializer):
    """Серіалізатор для фото ремонту"""
    
    class Meta:
        model = RepairPhoto
        fields = ['id', 'service_order', 'photo', 'photo_type', 'uploaded_at']
        read_only_fields = ['uploaded_at']


class ServiceOrderWriteSerializer(serializers.ModelSerializer):
    """
    Серіалізатор для СТВОРЕННЯ та ОНОВЛЕННЯ замовлень з підтримкою фото.
    """
    class Meta:
        model = ServiceOrder
        fields = [
            'id',
            'order_number',
            'client',
            'truck',
            'current_mileage',
            'problem_description',
            'status',
            'car_photo',
            'odometer_photo',
            'dashboard_photo',
        ]
        read_only_fields = ['id', 'order_number']


class ServiceOrderListSerializer(serializers.ModelSerializer):
    """
    Спрощений серіалізатор для СПИСКУ замовлень (тільки читання).
    """
    client = ClientSerializerForOrder(read_only=True)
    truck = TruckSerializerForOrder(read_only=True)
    
    class Meta:
        model = ServiceOrder
        fields = [
            'id', 'order_number', 'client', 'truck',
            'status', 'created_at', 'problem_description'
        ]


class ServiceOrderDetailSerializer(serializers.ModelSerializer):
    """
    Повний серіалізатор для ДЕТАЛЕЙ одного замовлення (тільки читання).
    """
    client = ClientSerializerForOrder(read_only=True)
    truck = TruckSerializerForOrder(read_only=True)
    works = ServiceWorkSerializer(many=True, read_only=True)
    photos = RepairPhotoSerializer(many=True, read_only=True)
    
    class Meta:
        model = ServiceOrder
        fields = [
            'id', 'order_number', 'client', 'truck',
            'current_mileage', 'problem_description',
            'status', 'created_at', 'updated_at',
            'works', 'photos', 'total_cost',
            'car_photo', 'odometer_photo', 'dashboard_photo',
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
