from django.contrib import admin
from .models import IgnoredVehicle, VehicleArrival


@admin.register(IgnoredVehicle)
class IgnoredVehicleAdmin(admin.ModelAdmin):
    list_display = ['license_plate', 'reason_type', 'description', 'is_active', 'added_by', 'created_at']
    list_filter = ['reason_type', 'is_active']
    search_fields = ['license_plate', 'description']
    readonly_fields = ['created_at']


@admin.register(VehicleArrival)
class VehicleArrivalAdmin(admin.ModelAdmin):
    list_display = ['license_plate', 'detected_at', 'client', 'truck', 'camera_id', 'ignored', 'notified']
    list_filter = ['ignored', 'notified', 'camera_id']
    search_fields = ['license_plate']
    readonly_fields = ['detected_at']
    date_hierarchy = 'detected_at'
