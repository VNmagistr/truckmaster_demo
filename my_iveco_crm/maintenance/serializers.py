# maintenance/serializers.py

from rest_framework import serializers
from .models import FluidChangeRecord, ServiceReminder, ServiceType


class ServiceTypeSerializer(serializers.ModelSerializer):
    """Серіалізатор для типів технічного обслуговування"""
    
    class Meta:
        model = ServiceType
        fields = [
            'id',
            'name',
            'description',
            'default_interval_km',
            'default_interval_months',
            'default_priority',
            'is_active',
            'sort_order',
        ]


class FluidChangeRecordSerializer(serializers.ModelSerializer):
    """Серіалізатор для записів про заміну рідин"""
    
    truck_display = serializers.StringRelatedField(source='truck', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = FluidChangeRecord
        fields = [
            'id',
            'truck',
            'truck_display',
            'subcategory',
            'subcategory_name',
            'product',
            'product_name',
            'quantity',
            'mileage',
            'next_change_mileage',
            'next_change_date',
            'service_order',
            'unit_price',
            'total_price',
            'notes',
            'performed_at',
            'created_by',
            'created_by_name',
            'created_at',
        ]
        read_only_fields = ['created_at', 'created_by', 'total_price']


class ServiceReminderSerializer(serializers.ModelSerializer):
    """Серіалізатор для нагадувань про ТО"""
    
    truck_display = serializers.StringRelatedField(source='truck', read_only=True)
    service_type_name = serializers.CharField(source='service_type.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    reminder_type_display = serializers.CharField(source='get_reminder_type_display', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceReminder
        fields = [
            'id',
            'truck',
            'truck_display',
            'title',
            'description',
            'service_type',
            'service_type_name',
            'reminder_type',
            'reminder_type_display',
            'target_mileage',
            'target_date',
            'status',
            'status_display',
            'priority',
            'priority_display',
            'completed_order',
            'completed_at',
            'is_overdue',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_is_overdue(self, obj):
        """Перевірка чи прострочено"""
        from django.utils import timezone
        
        if obj.status in ['completed', 'dismissed']:
            return False
        
        today = timezone.now().date()
        if obj.target_date and today > obj.target_date:
            return True
        
        return False


