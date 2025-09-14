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

# Цей серіалізатор будемо використовувати для списків (GET)
class TruckListSerializer(serializers.ModelSerializer):
    client = serializers.StringRelatedField()
    base_model = serializers.StringRelatedField()
    emission_standard = serializers.CharField(source='get_emission_standard_display') # Показує читабельну назву

    class Meta:
        model = Truck
        fields = [
            'id',
            'specific_model_name',
            'license_plate',
            'client',
            'client_id',
            'base_model',
            'current_mileage',
            'emission_standard', # Додали стандарт
            'last_seven_vin',
        ]

# А цей - для створення та редагування (POST, PUT)
class TruckDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Truck
        fields = '__all__' # Включаємо всі поля для можливості редагування