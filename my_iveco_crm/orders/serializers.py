from rest_framework import serializers
from .models import ServiceOrder, ServiceWork, Employee, Work, WorkCategory, RepairPhoto
from inventory.models import UsedPart
from clients.serializers import ClientSerializer, TruckListSerializer
from inventory.serializers import PartSerializer
import transaction # Імпортуємо транзакції для безпечного оновлення

# --- Спочатку визначаємо всі "прості" та допоміжні серіалізатори ---
# ... (RepairPhotoSerializer, EmployeeSerializer, etc. - без змін) ...
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

class WorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Work
        fields = ['id', 'name', 'price_per_hour']

class WorkCategorySerializer(serializers.ModelSerializer):
    works = WorkSerializer(many=True, read_only=True)
    class Meta:
        model = WorkCategory
        fields = ['id', 'name', 'works']

class ServiceWorkWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceWork
        fields = ['id', 'work', 'custom_description', 'duration_hours', 'employee']


# --- Тепер визначаємо основні ("композитні") серіалізатори ---

class ServiceOrderWriteSerializer(serializers.ModelSerializer):
    works = ServiceWorkWriteSerializer(many=True)

    class Meta:
        model = ServiceOrder
        fields = ['id', 'client', 'truck', 'status', 'start_date', 'works', 'order_number']
        extra_kwargs = {
            'order_number': {'required': False, 'allow_blank': True, 'allow_null': True}
        }

    def create(self, validated_data):
        works_data = validated_data.pop('works')
        order = ServiceOrder.objects.create(**validated_data)
        for work_data in works_data:
            ServiceWork.objects.create(service_order=order, **work_data)
        return order
        
    # --- ДОДАЄМО МЕТОД UPDATE ---
    def update(self, instance, validated_data):
        # Використовуємо транзакцію, щоб гарантувати цілісність даних
        with transaction.atomic():
            # Видаляємо старі роботи, пов'язані з цим замовленням
            instance.works.all().delete()
            
            # Створюємо нові роботи зі свіжих даних
            if 'works' in validated_data:
                works_data = validated_data.pop('works')
                for work_data in works_data:
                    ServiceWork.objects.create(service_order=instance, **work_data)

            # Оновлюємо решту полів самого замовлення
            instance = super().update(instance, validated_data)
            instance.save()
            return instance


# ... (решта серіалізаторів: ServiceOrderListSerializer, ServiceOrderDetailSerializer і т.д. без змін) ...
class ServiceOrderListSerializer(serializers.ModelSerializer):
    client = serializers.StringRelatedField(read_only=True)
    truck = serializers.StringRelatedField(read_only=True)
    status = serializers.CharField(source='get_status_display')

    class Meta:
        model = ServiceOrder
        fields = ['id', 'order_number', 'truck', 'client', 'status', 'start_date', 'total_cost']

class ServiceWorkDetailSerializer(serializers.ModelSerializer):
    work = WorkSerializer(read_only=True)
    employee = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = ServiceWork
        fields = ['id', 'work', 'custom_description', 'duration_hours', 'cost', 'employee']

class ServiceOrderDetailSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)
    truck = TruckListSerializer(read_only=True)
    status = serializers.CharField()
    works = ServiceWorkDetailSerializer(many=True, read_only=True)
    repair_photos = RepairPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceOrder
        fields = [
            'id', 'order_number', 'client', 'truck', 'status', 'start_date', 'end_date', 
            'total_cost', 'works', 'repair_photos', 'car_photo', 'odometer_photo'
        ]