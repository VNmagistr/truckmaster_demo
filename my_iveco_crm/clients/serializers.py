from rest_framework import serializers
from .models import Client, Truck, IvecoBaseModel

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__' # Включаємо всі поля

class TruckSerializer(serializers.ModelSerializer):
    # Робимо так, щоб у відповіді API відображались не ID, а назви
    client = serializers.StringRelatedField()
    base_model = serializers.StringRelatedField()

    class Meta:
        model = Truck
        fields = [
            'id', 
            'specific_model_name', 
            'license_plate', 
            'client', 
            'base_model', 
            'current_mileage'
        ]