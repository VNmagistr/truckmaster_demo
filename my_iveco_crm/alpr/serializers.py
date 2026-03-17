from rest_framework import serializers
from .models import IgnoredVehicle, VehicleArrival


class IgnoredVehicleSerializer(serializers.ModelSerializer):
    added_by_name = serializers.CharField(source='added_by.get_full_name', read_only=True)
    reason_type_display = serializers.CharField(source='get_reason_type_display', read_only=True)

    class Meta:
        model = IgnoredVehicle
        fields = [
            'id', 'license_plate', 'reason_type', 'reason_type_display',
            'description', 'is_active', 'added_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'added_by_name', 'reason_type_display']


class VehicleArrivalSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    truck_info = serializers.SerializerMethodField()
    appointment_info = serializers.SerializerMethodField()

    class Meta:
        model = VehicleArrival
        fields = [
            'id', 'license_plate', 'detected_at', 'camera_id', 'confidence',
            'truck_id', 'truck_info', 'client_id', 'client_name',
            'appointment_id', 'appointment_info',
            'ignored', 'ignore_reason', 'notified',
        ]
        read_only_fields = fields

    def get_truck_info(self, obj):
        if not obj.truck:
            return None
        return {
            'id': obj.truck.id,
            'license_plate': obj.truck.license_plate,
            'specific_model_name': obj.truck.specific_model_name,
        }

    def get_appointment_info(self, obj):
        if not obj.appointment:
            return None
        return {
            'id': obj.appointment.id,
            'scheduled_dt': obj.appointment.scheduled_dt,
            'service_type': obj.appointment.service_type,
            'status': obj.appointment.status,
        }


class AlprEventInputSerializer(serializers.Serializer):
    """Вхідні дані від ALPR-скрипта / камери."""
    license_plate = serializers.CharField(max_length=20)
    camera_id = serializers.CharField(max_length=100, required=False, default='')
    confidence = serializers.FloatField(required=False, allow_null=True)
