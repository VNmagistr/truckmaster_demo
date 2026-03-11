from rest_framework import serializers
from .models import Client, Truck, IvecoBaseModel

class ClientSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True, default=None)

    class Meta:
        model = Client
        fields = ['id', 'name', 'phone', 'email', 'address', 'marked_for_deletion']

    def validate_phone(self, value):
        return value if value else None

    def validate_email(self, value):
        return value if value else None

class IvecoBaseModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = IvecoBaseModel
        fields = '__all__'

class ClientBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name']

# Цей серіалізатор будемо використовувати для списків (GET)
class TruckListSerializer(serializers.ModelSerializer):
    client = ClientBriefSerializer(read_only=True)
    base_model = serializers.StringRelatedField()

    class Meta:
        model = Truck
        fields = [
            'id',
            'specific_model_name',
            'license_plate',
            'client',
            'client_id',
            'base_model',
            'last_seven_vin',
            'marked_for_deletion',
        ]

# А цей - для створення та редагування (POST, PUT)
class TruckDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Truck
        fields = '__all__'
        read_only_fields = ['last_seven_vin']
