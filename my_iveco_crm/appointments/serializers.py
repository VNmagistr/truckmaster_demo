from rest_framework import serializers
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    end_dt = serializers.DateTimeField(read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'client', 'client_name', 'client_phone', 'license_plate',
            'scheduled_dt', 'duration_minutes', 'end_dt',
            'service_type', 'service_type_display',
            'description', 'status', 'status_display',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'converted_to_order', 'confirmation_sent', 'reminder_sent',
        ]
        read_only_fields = ['created_by', 'confirmation_sent', 'reminder_sent', 'converted_to_order']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None
