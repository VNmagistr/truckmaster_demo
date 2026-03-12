from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['client_name', 'client_phone', 'license_plate', 'scheduled_dt', 'service_type', 'status']
    list_filter = ['status', 'service_type']
    search_fields = ['client_name', 'client_phone', 'license_plate']
    readonly_fields = ['created_by', 'created_at', 'updated_at', 'confirmation_sent', 'reminder_sent']
    date_hierarchy = 'scheduled_dt'
