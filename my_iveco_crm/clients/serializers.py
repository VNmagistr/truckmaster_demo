from rest_framework import serializers
from .models import Client, Truck, IvecoBaseModel, OwnershipHistory

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'phone', 'email', 'address', 'notes', 'marked_for_deletion']
        extra_kwargs = {
            'phone': {'required': False, 'allow_blank': True, 'allow_null': True},
            'email': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

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
    euro_standard_display = serializers.CharField(
        source='get_euro_standard_display', read_only=True
    )
    transmission_type_display = serializers.CharField(
        source='get_transmission_type_display', read_only=True
    )

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
            'euro_standard',
            'euro_standard_display',
            'transmission_type',
            'transmission_type_display',
            'marked_for_deletion',
        ]

class OwnershipHistorySerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', default=None, read_only=True)
    client_id = serializers.IntegerField(source='client.id', default=None, read_only=True)

    class Meta:
        model = OwnershipHistory
        fields = ['id', 'client_name', 'client_id', 'license_plate', 'change_date']


# А цей - для створення та редагування (POST, PUT)
class TruckDetailSerializer(serializers.ModelSerializer):
    ownership_history = OwnershipHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Truck
        fields = '__all__'
        read_only_fields = ['last_seven_vin']
