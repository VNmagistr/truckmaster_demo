from rest_framework import serializers
from django.db import transaction
from .models import ServiceOrder, ServiceWork, Employee, Work, WorkCategory, RepairPhoto
from inventory.models import UsedPart
from clients.serializers import ClientSerializer, TruckListSerializer
from inventory.serializers import PartSerializer

class RepairPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairPhoto
        fields = ['id', 'image', 'caption', 'uploaded_at']

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
        fields = ['id', 'name']

class WorkCategorySerializer(serializers.ModelSerializer):
    works = WorkSerializer(many=True, read_only=True)
    class Meta:
        model = WorkCategory
        fields = ['id', 'name', 'price_per_hour', 'works']

class ServiceWorkWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceWork
        fields = ['id', 'work', 'custom_description', 'duration_hours', 'employee']

class ServiceOrderWriteSerializer(serializers.ModelSerializer):
    works = ServiceWorkWriteSerializer(many=True, required=False)
    repair_photos_upload = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )

    class Meta:
        model = ServiceOrder
        fields = [
            'id', 'client', 'truck', 'status', 'start_date', 'works', 'order_number',
            'car_photo', 'odometer_photo', 'dashboard_photo', 'repair_photos_upload'
        ]
        extra_kwargs = {
            'order_number': {'required': False, 'allow_blank': True, 'allow_null': True},
            'car_photo': {'required': False, 'allow_null': True},
            'odometer_photo': {'required': False, 'allow_null': True},
            'dashboard_photo': {'required': False, 'allow_null': True},
        }

    def create(self, validated_data):
        works_data = validated_data.pop('works', [])
        photos_data = validated_data.pop('repair_photos_upload', [])
        
        order = ServiceOrder.objects.create(**validated_data)
        
        for work_data in works_data:
            ServiceWork.objects.create(service_order=order, **work_data)
            
        for photo_file in photos_data:
            RepairPhoto.objects.create(service_order=order, image=photo_file)
            
        return order

    def update(self, instance, validated_data):
        with transaction.atomic():
            if 'works' in validated_data:
                instance.works.all().delete()
                works_data = validated_data.pop('works')
                for work_data in works_data:
                    ServiceWork.objects.create(service_order=instance, **work_data)
            
            if 'repair_photos_upload' in validated_data:
                photos_data = validated_data.pop('repair_photos_upload')
                for photo_file in photos_data:
                    RepairPhoto.objects.create(service_order=instance, image=photo_file)

            instance = super().update(instance, validated_data)
            instance.save()
            return instance

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
    status = serializers.CharField(source='get_status_display')
    works = ServiceWorkDetailSerializer(many=True, read_only=True)
    repair_photos = RepairPhotoSerializer(many=True, read_only=True)
    class Meta:
        model = ServiceOrder
        fields = [
            'id', 'order_number', 'client', 'truck', 'status', 'start_date', 'end_date', 
            'total_cost', 'works', 'repair_photos', 'car_photo', 'odometer_photo', 'dashboard_photo'
        ]