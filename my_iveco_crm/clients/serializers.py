from rest_framework import serializers
from .models import Client, Truck, IvecoBaseModel

class ClientSerializer(serializers.ModelSerializer):
    marked_for_deletion_by_name = serializers.CharField(
        source='marked_for_deletion_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = Client
        fields = [
            'id',
            'name',
            'phone',
            'email',
            'address',
            'telegram_chat_id',
            'marked_for_deletion',
            'marked_for_deletion_by',
            'marked_for_deletion_by_name',
            'marked_for_deletion_at',
            'deletion_reason',
        ]
        read_only_fields = [
            'marked_for_deletion',
            'marked_for_deletion_by',
            'marked_for_deletion_at',
            'deletion_reason',
        ]

class IvecoBaseModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = IvecoBaseModel
        fields = '__all__'

class TruckListSerializer(serializers.ModelSerializer):
    client = serializers.StringRelatedField()
    base_model = serializers.StringRelatedField()
    clientName = serializers.CharField(source='client.name', read_only=True)
    
    class Meta:
        model = Truck
        fields = [
            'id',
            'specific_model_name',
            'license_plate',
            'client',
            'client_id',
            'clientName',
            'base_model',
            'last_seven_vin',
            'marked_for_deletion',
        ]

class TruckDetailSerializer(serializers.ModelSerializer):
    marked_for_deletion_by_name = serializers.CharField(
        source='marked_for_deletion_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = Truck
        fields = [
            'id',
            'client',
            'base_model',
            'specific_model_name',
            'full_vin',
            'last_seven_vin',
            'license_plate',
            'euro_standard',
            'marked_for_deletion',
            'marked_for_deletion_by',
            'marked_for_deletion_by_name',
            'marked_for_deletion_at',
            'deletion_reason',
        ]
        read_only_fields = [
            'last_seven_vin',
            'marked_for_deletion',
            'marked_for_deletion_by',
            'marked_for_deletion_at',
            'deletion_reason',
        ]
        