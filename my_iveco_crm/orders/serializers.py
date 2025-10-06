from rest_framework import serializers
from .models import ServiceOrder, ServiceWork, Employee, Work, WorkCategory, RepairPhoto
from inventory.models import UsedPart
from clients.serializers import ClientSerializer, TruckListSerializer
from inventory.serializers import PartSerializer

# --- НОВІ СЕРІАЛІЗАТОРИ ---
class WorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Work
        fields = ['id', 'name', 'price']

class WorkCategorySerializer(serializers.ModelSerializer):
    works = WorkSerializer(many=True, read_only=True)

    class Meta:
        model = WorkCategory
        fields = ['id', 'name', 'works']

# --- ОНОВЛЕНІ СЕРІАЛІЗАТОРИ ---
class ServiceWorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceWork
        # Фронтенд надсилає ID роботи з прайсу, опис і вартість (яка може бути змінена)
        fields = ['id', 'work', 'custom_description', 'cost']

class ServiceOrderWriteSerializer(serializers.ModelSerializer):
    works = ServiceWorkSerializer(many=True)

    class Meta:
        model = ServiceOrder
        fields = ['id', 'client', 'truck', 'status', 'start_date', 'works']

    def create(self, validated_data):
        works_data = validated_data.pop('works')
        order = ServiceOrder.objects.create(**validated_data)
        for work_data in works_data:
            ServiceWork.objects.create(service_order=order, **work_data)
        return order

# --- Серіалізатори для читання (оновлені відповідно до нових моделей) ---
class ServiceWorkDetailSerializer(serializers.ModelSerializer):
    work = WorkSerializer(read_only=True) # Показуємо повну інформацію про роботу
    employee = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = ServiceWork
        fields = ['id', 'work', 'custom_description', 'cost', 'employee']

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

class ServiceOrderListSerializer(serializers.ModelSerializer):
    client = serializers.StringRelatedField(read_only=True)
    truck = serializers.StringRelatedField(read_only=True)
    status = serializers.CharField(source='get_status_display')

    class Meta:
        model = ServiceOrder
        fields = ['id', 'truck', 'client', 'status', 'start_date', 'total_cost']

# --- Існуючі серіалізатори, які залишаються без змін ---
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