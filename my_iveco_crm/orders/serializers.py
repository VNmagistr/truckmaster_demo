from rest_framework import serializers
from .models import (
    ServiceOrder, ServiceWork, Employee, WorkGroup, WorkPrice, 
    RepairPhoto, MaintenanceRule, MaintenanceLog
)
from clients.models import Client, Truck
from inventory.models import UsedPart

# ----- Серіалізатори для Клієнтів та Вантажівок (для відображення в замовленнях) -----
class ClientSerializerForOrder(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'phone']

class TruckSerializerForOrder(serializers.ModelSerializer):
    class Meta:
        model = Truck
        fields = ['id', 'license_plate', 'specific_model_name', 'last_seven_vin']

# ----- Серіалізатори для додатку Orders -----

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'

class WorkGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkGroup
        fields = '__all__'

class WorkPriceSerializer(serializers.ModelSerializer):
    """Серіалізатор для робіт з прайсу"""
    
    # Додаємо розраховані поля
    price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True,
        source='get_calculated_price'
    )
    hourly_rate = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        source='work_group.hourly_rate'
    )
    work_group_name = serializers.CharField(
        read_only=True,
        source='work_group.name'
    )
    
    class Meta:
        model = WorkPrice
        fields = [
            'id',
            'work_group',
            'work_group_name',
            'name',
            'standard_hours',
            'hourly_rate',
            'price',  # Розрахункове поле
        ]
        read_only_fields = ['price', 'hourly_rate', 'work_group_name']


# Якщо потрібен окремий serializer для створення/оновлення
class WorkPriceWriteSerializer(serializers.ModelSerializer):
    """Серіалізатор для створення/оновлення робіт"""
    
    class Meta:
        model = WorkPrice
        fields = ['work_group', 'name', 'standard_hours']

class UsedPartSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsedPart
        fields = '__all__'

# --- Серіалізатори Виконаних Робіт (ServiceWork) ---

class ServiceWorkSerializer(serializers.ModelSerializer):
    """
    Серіалізатор для ЧИТАННЯ робіт (з деталями).
    """
    # 👇 ОНОВЛЕНО: 'work_group' замінено на 'work' 👇
    work = WorkPriceSerializer(read_only=True)
    employee = EmployeeSerializer(read_only=True)
    used_parts = UsedPartSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceWork
        fields = '__all__'

class ServiceWorkWriteSerializer(serializers.ModelSerializer):
    """
    Серіалізатор для СТВОРЕННЯ/ОНОВЛЕННЯ робіт.
    Приймає ID для пов'язаних полів.
    """
    class Meta:
        model = ServiceWork
        # 👇 ОНОВЛЕНО: 'work_group' замінено на 'work' 👇
        fields = [
            'service_order', 
            'work', 
            'description', 
            'employee', 
            'hours_spent'
        ]

class RepairPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairPhoto
        fields = '__all__'

# --- Серіалізатори Замовлень (ServiceOrder) ---

class ServiceOrderWriteSerializer(serializers.ModelSerializer):
    """
    Простий серіалізатор для СТВОРЕННЯ та ОНОВЛЕННЯ замовлень.
    """
    class Meta:
        model = ServiceOrder
        fields = [
            'order_number', 
            'client',
            'truck',
            'problem_description', 
            'status'
        ]

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
            'problem_description', 'status', 'created_at', 'updated_at',
            'works', 'photos'
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