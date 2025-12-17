from rest_framework import serializers
from .models import Client, Truck, IvecoBaseModel

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'

class IvecoBaseModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = IvecoBaseModel
        fields = '__all__'


class TruckListSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    base_model = serializers.StringRelatedField()
    emission_standard = serializers.CharField(source='get_euro_standard_display')
    
    class Meta:
        model = Truck
        fields = [
            'id',
            'specific_model_name',
            'license_plate',
            'client_id',
            'client_name',
            'base_model',
            'emission_standard',
            'last_seven_vin',
        ]


class TruckDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Truck
        fields = '__all__'