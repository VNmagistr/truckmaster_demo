from rest_framework import serializers
from .models import Client, Truck, IvecoBaseModel


class ClientSerializer(serializers.ModelSerializer):
    """Серіалізатор для клієнтів"""
    
    class Meta:
        model = Client
        fields = [
            'id',
            'name',
            'phone',  # ✅ ВАЖЛИВО: phone має бути тут
            'email',
            'address',
            'telegram_chat_id',
            'marked_for_deletion',
            'marked_for_deletion_by',
            'marked_for_deletion_at',
            'deletion_reason',
        ]
        read_only_fields = [
            'marked_for_deletion_by',
            'marked_for_deletion_at',
        ]


class IvecoBaseModelSerializer(serializers.ModelSerializer):
    """Серіалізатор для базових моделей Iveco"""
    
    class Meta:
        model = IvecoBaseModel
        fields = '__all__'


class TruckListSerializer(serializers.ModelSerializer):
    """Серіалізатор для списку вантажівок"""
    client_name = serializers.CharField(source='client.name', read_only=True)  # ✅ ДОДАНО
    base_model_name = serializers.CharField(source='base_model.name', read_only=True)
    euro_standard_display = serializers.CharField(source='get_euro_standard_display', read_only=True)

    class Meta:
        model = Truck
        fields = [
            'id',
            'specific_model_name',
            'license_plate',
            'client',
            'client_name',  # ✅ ДОДАНО: для відображення імені клієнта
            'base_model',
            'base_model_name',
            'euro_standard',
            'euro_standard_display',
            'last_seven_vin',
            'marked_for_deletion',
        ]


class TruckDetailSerializer(serializers.ModelSerializer):
    """Серіалізатор для деталей вантажівки"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    base_model_name = serializers.CharField(source='base_model.name', read_only=True)
    marked_for_deletion_by_name = serializers.CharField(
        source='marked_for_deletion_by.get_full_name',
        read_only=True
    )

    class Meta:
        model = Truck
        fields = [
            'id',
            'client',
            'client_name',
            'base_model',
            'base_model_name',
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
            'marked_for_deletion_by',
            'marked_for_deletion_at',
        ]
        