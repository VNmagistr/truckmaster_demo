from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    ServiceOrder, ServiceWork, WorkGroup, WorkPrice,
    RepairPhoto, MaintenanceRule, MaintenanceLog, MaintenanceKit, MaintenanceKitFilter,
    TruckMaintenanceIntervals,
)
from clients.models import Client, Truck
from inventory.models import UsedPart

User = get_user_model()


class ClientSerializerForOrder(serializers.ModelSerializer):
    """Серіалізатор клієнта для відображення в замовленні."""
    
    class Meta:
        model = Client
        fields = ['id', 'name', 'phone']


class TruckSerializerForOrder(serializers.ModelSerializer):
    """
    Серіалізатор вантажівки для відображення в замовленні.
    Виправлено: безпечна обробка NULL значень для client.
    """
    client_name = serializers.SerializerMethodField()
    client_id = serializers.SerializerMethodField()

    class Meta:
        model = Truck
        fields = ['id', 'license_plate', 'specific_model_name', 'last_seven_vin', 'client_id', 'client_name']

    def get_client_name(self, obj):
        """Безпечне отримання імені клієнта."""
        try:
            if obj.client:
                return obj.client.name
        except Exception:
            pass
        return None

    def get_client_id(self, obj):
        """Безпечне отримання ID клієнта."""
        try:
            if obj.client:
                return obj.client.id
        except Exception:
            pass
        return None


class MechanicSerializer(serializers.ModelSerializer):
    """Серіалізатор механіка."""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name']
        
    def get_full_name(self, obj):
        """Отримання повного імені механіка."""
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class WorkGroupSerializer(serializers.ModelSerializer):
    """Серіалізатор групи робіт."""
    
    class Meta:
        model = WorkGroup
        fields = '__all__'


class WorkPriceSerializer(serializers.ModelSerializer):
    """Серіалізатор ціни роботи."""
    calculated_price = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkPrice
        fields = '__all__'
    
    def get_calculated_price(self, obj):
        """Отримання розрахованої ціни."""
        try:
            return obj.get_calculated_price()
        except Exception:
            return 0


class UsedPartSerializer(serializers.ModelSerializer):
    """Серіалізатор використаної запчастини."""
    part_name = serializers.CharField(source='part.name', read_only=True)
    part_sku = serializers.CharField(source='part.sku_code', read_only=True)
    part_brand = serializers.CharField(source='part.brand', read_only=True)

    class Meta:
        model = UsedPart
        fields = '__all__'


class ServiceWorkSerializer(serializers.ModelSerializer):
    """Серіалізатор виконаної роботи для читання."""
    work = WorkPriceSerializer(read_only=True)
    mechanic = MechanicSerializer(read_only=True)
    used_parts = UsedPartSerializer(many=True, read_only=True)
    amount = serializers.SerializerMethodField()

    class Meta:
        model = ServiceWork
        fields = '__all__'
    
    def get_amount(self, obj):
        """Отримання суми за роботу."""
        try:
            return obj.amount
        except Exception:
            return 0


class ServiceWorkWriteSerializer(serializers.ModelSerializer):
    """Серіалізатор виконаної роботи для запису."""
    
    class Meta:
        model = ServiceWork
        fields = ['service_order', 'work', 'description', 'mechanic', 'hours_spent']


class RepairPhotoSerializer(serializers.ModelSerializer):
    """Серіалізатор фото ремонту."""
    
    class Meta:
        model = RepairPhoto
        fields = '__all__'


class ServiceOrderWriteSerializer(serializers.ModelSerializer):
    """Серіалізатор замовлення для запису."""
    
    class Meta:
        model = ServiceOrder
        fields = '__all__'

    def validate(self, data):
        """Автоматичне заповнення клієнта з вантажівки."""
        truck = data.get('truck')
        client = data.get('client')

        if truck and not client:
            if truck.client:
                data['client'] = truck.client
        return data


class ServiceOrderListSerializer(serializers.ModelSerializer):
    """Серіалізатор замовлення для списку."""
    client = ClientSerializerForOrder(read_only=True)
    truck = TruckSerializerForOrder(read_only=True)
    marked_for_deletion_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ServiceOrder
        fields = [
            'id', 
            'order_number', 
            'client', 
            'truck', 
            'status', 
            'total_cost',
            'created_at', 
            'marked_for_deletion',
            'marked_for_deletion_by_name'
        ]

    def get_marked_for_deletion_by_name(self, obj):
        """Безпечне отримання імені користувача, який позначив на видалення."""
        try:
            if obj.marked_for_deletion_by:
                u = obj.marked_for_deletion_by
                return f"{u.first_name} {u.last_name}".strip() or u.username
        except Exception:
            pass
        return None


class ServiceOrderDetailSerializer(serializers.ModelSerializer):
    """Серіалізатор замовлення для детального перегляду."""
    client = ClientSerializerForOrder(read_only=True)
    truck = TruckSerializerForOrder(read_only=True)
    works = ServiceWorkSerializer(many=True, read_only=True)
    photos = RepairPhotoSerializer(many=True, read_only=True)
    direct_parts = UsedPartSerializer(many=True, read_only=True)
    marked_for_deletion_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ServiceOrder
        fields = [
            'id',
            'order_number',
            'client',
            'truck',
            'problem_description',
            'recommendations',
            'current_mileage',
            'status',
            'created_at',
            'updated_at',
            'total_cost',
            'car_photo',
            'odometer_photo',
            'dashboard_photo',
            'works',
            'direct_parts',
            'photos',
            'marked_for_deletion',
            'marked_for_deletion_by',
            'marked_for_deletion_by_name',
            'marked_for_deletion_at',
            'deletion_reason',
        ]
        
    def get_marked_for_deletion_by_name(self, obj):
        """Безпечне отримання імені користувача, який позначив на видалення."""
        try:
            if obj.marked_for_deletion_by:
                u = obj.marked_for_deletion_by
                return f"{u.first_name} {u.last_name}".strip() or u.username
        except Exception:
            pass
        return None


class MaintenanceRuleSerializer(serializers.ModelSerializer):
    """Серіалізатор правила ТО."""
    
    class Meta:
        model = MaintenanceRule
        fields = '__all__'


class MaintenanceLogSerializer(serializers.ModelSerializer):
    """Серіалізатор журналу ТО."""
    rule_name = serializers.CharField(source='rule.name', read_only=True)

    class Meta:
        model = MaintenanceLog
        fields = ['id', 'truck', 'rule', 'rule_name', 'date_performed', 'mileage']


class MaintenanceKitFilterSerializer(serializers.ModelSerializer):
    """Серіалізатор фільтра в комплекті ТО."""
    part_name = serializers.SerializerMethodField()
    part_sku = serializers.CharField(source='part.sku_code', read_only=True)
    part_display = serializers.SerializerMethodField()

    class Meta:
        model = MaintenanceKitFilter
        fields = ['id', 'maintenance_kit', 'part', 'part_name', 'part_sku', 'part_display', 'quantity', 'change_interval_km']

    def get_part_name(self, obj):
        return str(obj.part) if obj.part else None

    def get_part_display(self, obj):
        return str(obj.part) if obj.part else None


class MaintenanceKitSerializer(serializers.ModelSerializer):
    """Серіалізатор комплекту ТО — повний (для читання)."""
    filters = MaintenanceKitFilterSerializer(many=True, read_only=True)
    oil_name = serializers.SerializerMethodField()
    oil_sku = serializers.CharField(source='oil.sku_code', read_only=True)

    def get_oil_name(self, obj):
        return str(obj.oil) if obj.oil else None
    truck_display = serializers.CharField(source='truck.__str__', read_only=True)

    class Meta:
        model = MaintenanceKit
        fields = ['id', 'truck', 'truck_display', 'oil', 'oil_name', 'oil_sku', 'oil_quantity', 'oil_change_interval_km', 'filters']


class MaintenanceKitWriteSerializer(serializers.ModelSerializer):
    """Серіалізатор комплекту ТО — для створення та редагування."""

    class Meta:
        model = MaintenanceKit
        fields = ['id', 'truck', 'oil', 'oil_quantity', 'oil_change_interval_km']


class TruckMaintenanceIntervalsSerializer(serializers.ModelSerializer):
    """Серіалізатор інтервалів ТО — для читання та редагування."""

    class Meta:
        model = TruckMaintenanceIntervals
        fields = [
            'id', 'truck',
            'engine_oil_interval', 'engine_oil_last_km',
            'gearbox_oil_interval', 'gearbox_oil_last_km',
            'rear_axle_oil_interval', 'rear_axle_oil_last_km',
            'belts_interval', 'belts_last_km',
            'chains_interval', 'chains_last_km',
        ]