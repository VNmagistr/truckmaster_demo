from django.contrib import admin
from .models import Part, UsedPart

@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku_code', 'current_stock', 'price')
    search_fields = ('name', 'sku_code')
    list_filter = ('current_stock',)

@admin.register(UsedPart)
class UsedPartAdmin(admin.ModelAdmin):
    list_display = ('service_work', 'part', 'quantity')
    search_fields = ('service_work__job_description', 'part__name')