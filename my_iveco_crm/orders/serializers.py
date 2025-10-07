# orders/serializers.py

from rest_framework import serializers
from .models import ServiceOrder, ServiceWork, Employee, Work, WorkCategory, RepairPhoto
from inventory.models import UsedPart
from clients.serializers import ClientSerializer, TruckListSerializer
from inventory.serializers import PartSerializer

# --- 1. СПОЧАТКУ ВИЗНАЧАЄМО ВСІ "ПРОСТІ" ТА ДОПОМІЖНІ СЕРІАЛІЗАТОРИ ---

class RepairPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairPhoto
        fields = '__all__'

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['id', 'name', 'position']

class UsedPartSerializer(serializers.ModelSerializer):
    part = PartSerializer(read_only=True)
    class Meta:
        model = UsedPart
        fields = ['id', 'part', 'quantity']

# Серіалізатор для однієї роботи з прайс-листа
class WorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Work
        fields = ['id', 'name', 'price_per_hour'] # Використовуємо 'price_per_hour'

# Серіалізатор для Категорії робіт (включає вкладений список робіт)
class WorkCategorySerializer(serializers.ModelSerializer):
    works = WorkSerializer(many=True, read_only=True)

    class Meta:
        model = WorkCategory
        fields = ['id', 'name', 'works']

# Серіалізатор для ОДНІЄЇ виконаної роботи (для ЗАПИСУ в замовлення)
class ServiceWorkWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceWork
        # Фронтенд надсилає ID роботи, опис і кількість годин
        fields = ['id', 'work', 'custom_description', 'duration_hours', 'employee']

# --- 2. ТЕПЕР ВИЗНАЧАЄМО ОСНОВНІ ("КОМПОЗИТНІ") СЕРІАЛІЗАТОРИ ---

# Серіалізатор для ЗАПИСУ (створення/оновлення) замовлення
class ServiceOrderWriteSerializer(serializers.ModelSerializer):
    works = ServiceWorkWriteSerializer(many=True)

    class Meta:
        model = ServiceOrder
        fields = ['id', 'client', 'truck', 'status', 'start_date', 'works']

    def create(self, validated_data):
        works_data = validated_data.pop('works')
        order = ServiceOrder.objects.create(**validated_data)
        for work_data in works_data:
            ServiceWork.objects.create(service_order=order, **work_data)
        # Можна додати виклик update_total_cost після створення, якщо потрібно
        # order.update_total_cost() 
        return order
        
    def update(self, instance, validated_data):
        # Логіка для оновлення замовлення та його робіт (за потреби)
        # ...
        return super().update(instance, validated_data)


# Серіалізатор для ЧИТАННЯ (список замовлень)
class ServiceOrderListSerializer(serializers.ModelSerializer):
    client = serializers.StringRelatedField(read_only=True)
    truck = serializers.StringRelatedField(read_only=True)
    status = serializers.CharField(source='get_status_display')

    class Meta:
        model = ServiceOrder
        fields = ['id', 'truck', 'client', 'status', 'start_date', 'total_cost']

# Окремий детальний серіалізатор для вкладених робіт (для ЧИТАННЯ)
class ServiceWorkDetailSerializer(serializers.ModelSerializer):
    work = WorkSerializer(read_only=True)
    employee = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = ServiceWork
        fields = ['id', 'work', 'custom_description', 'duration_hours', 'cost', 'employee']

# Серіалізатор для ЧИТАННЯ (детальна сторінка замовлення)
class ServiceOrderDetailSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)
    truck = TruckListSerializer(read_only=True)
    status = serializers.CharField(source='get_status_display')
    works = ServiceWorkDetailSerializer(many=True, read_only=True)
    repair_photos = RepairPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceOrder
        fields = [
            'id', 'client', 'truck', 'status', 'start_date', 'end_date', 
            'total_cost', 'works', 'repair_photos', 'car_photo', 'odometer_photo'
        ]