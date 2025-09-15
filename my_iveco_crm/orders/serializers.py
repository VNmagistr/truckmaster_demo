from rest_framework import serializers
from .models import ServiceOrder, ServiceWork, Employee
from inventory.models import UsedPart
from clients.serializers import ClientSerializer, TruckListSerializer
from inventory.serializers import PartSerializer

# НОВИЙ СЕРІАЛІЗАТОР
class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['id', 'name', 'position']

class UsedPartSerializer(serializers.ModelSerializer):
    part = PartSerializer(read_only=True)

    class Meta:
        model = UsedPart
        fields = ['id', 'part', 'quantity']

class ServiceWorkSerializer(serializers.ModelSerializer):
    used_parts = UsedPartSerializer(many=True, read_only=True)
    # Додаємо поле employee, щоб воно було в POST/PUT запитах
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())

    class Meta:
        model = ServiceWork
        # 'employee' додано до списку
        fields = ['id', 'job_description', 'labor_cost', 'duration_hours', 'used_parts', 'employee', 'service_order']
        # service_order потрібен для створення/оновлення
        extra_kwargs = {'service_order': {'write_only': True}}

# Серіалізатор для відображення у списку (залишається простим)
class ServiceOrderListSerializer(serializers.ModelSerializer):
    client = serializers.StringRelatedField(read_only=True)
    truck = serializers.StringRelatedField(read_only=True)
    status = serializers.CharField(source='get_status_display')

    class Meta:
        model = ServiceOrder
        fields = ['id', 'truck', 'client', 'status', 'start_date', 'total_cost']

# Серіалізатор для детальної сторінки (тепер з вкладеними даними)
class ServiceOrderDetailSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)
    truck = TruckListSerializer(read_only=True)
    status = serializers.CharField(source='get_status_display')
    works = ServiceWorkSerializer(many=True, read_only=True) # Вкладаємо роботи

    class Meta:
        model = ServiceOrder
        fields = '__all__'