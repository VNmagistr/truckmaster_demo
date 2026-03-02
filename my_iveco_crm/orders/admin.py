from django.contrib import admin
from .models import (
    ServiceOrder, ServiceWork, WorkGroup, WorkPrice,
    MaintenanceKit, MaintenanceKitFilter, MaintenanceRule,
    MaintenanceLog, RepairPhoto, TruckMaintenanceIntervals,
)


class ServiceWorkInline(admin.StackedInline):
    model = ServiceWork
    extra = 0
    autocomplete_fields = ['work', 'mechanic']


class MaintenanceKitFilterInline(admin.TabularInline):
    model = MaintenanceKitFilter
    extra = 1

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'part':
            from inventory.models import Product
            from django.db.models import Q
            FILTER_TYPES = {'filter', 'фільтр', 'фільтри'}
            kwargs['queryset'] = Product.objects.filter(
                Q(subcategory__category__category_type__in=list(FILTER_TYPES)) |
                Q(subcategory__category__name__icontains='фільтр') |
                Q(name__iregex=r'^фільтр')
            ).filter(marked_for_deletion=False).order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(WorkGroup)
class WorkGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'hourly_rate')
    search_fields = ('name',)


@admin.register(WorkPrice)
class WorkPriceAdmin(admin.ModelAdmin):
    list_display = ('name', 'work_group', 'standard_hours', 'price')
    list_filter = ('work_group',)
    search_fields = ('name',)
    autocomplete_fields = ['work_group']


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'truck', 'client', 'status', 'total_cost', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'truck__license_plate', 'client__name')
    autocomplete_fields = ['client', 'truck']
    inlines = [ServiceWorkInline]
    readonly_fields = ('total_cost', 'created_at', 'updated_at')

    fieldsets = (
        ('Основне', {
            'fields': ('order_number', 'client', 'truck', 'status')
        }),
        ('Деталі', {
            'fields': ('current_mileage', 'problem_description')
        }),
        ('Фото', {
            'fields': ('car_photo', 'odometer_photo', 'dashboard_photo'),
            'classes': ('collapse',)
        }),
        ('Вартість', {
            'fields': ('total_cost',)
        }),
        ('Дати', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ServiceWork)
class ServiceWorkAdmin(admin.ModelAdmin):
    list_display = ('service_order', 'work', 'mechanic', 'hours_spent', 'amount')
    list_filter = ('work__work_group',)
    search_fields = ('service_order__order_number', 'work__name')
    autocomplete_fields = ['service_order', 'work', 'mechanic']


@admin.register(RepairPhoto)
class RepairPhotoAdmin(admin.ModelAdmin):
    list_display = ('service_order', 'description')
    search_fields = ('service_order__order_number', 'description')


@admin.register(MaintenanceRule)
class MaintenanceRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'km_interval')
    search_fields = ('name',)
    filter_horizontal = ('applicable_models',)


@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ('truck', 'rule', 'date_performed', 'mileage')
    list_filter = ('rule', 'date_performed')
    search_fields = ('truck__license_plate',)
    autocomplete_fields = ['truck', 'rule']


@admin.register(MaintenanceKit)
class MaintenanceKitAdmin(admin.ModelAdmin):
    list_display = ('truck', 'oil', 'oil_quantity', 'oil_change_interval_km')
    search_fields = ('truck__license_plate',)
    autocomplete_fields = ['truck']
    inlines = [MaintenanceKitFilterInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'oil':
            from inventory.models import Product
            from django.db.models import Q
            OIL_TYPES = {'oil', 'олива', 'масло', 'мастило'}
            kwargs['queryset'] = Product.objects.filter(
                Q(subcategory__category__category_type__in=list(OIL_TYPES)) |
                Q(name__iregex=r'^олива') |
                Q(name__icontains='олива моторна') |
                Q(name__iregex=r'^масло\s+мотор')
            ).filter(marked_for_deletion=False).order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(MaintenanceKitFilter)
class MaintenanceKitFilterAdmin(admin.ModelAdmin):
    list_display = ('maintenance_kit', 'part', 'quantity', 'change_interval_km')
    autocomplete_fields = ['maintenance_kit', 'part']


@admin.register(TruckMaintenanceIntervals)
class TruckMaintenanceIntervalsAdmin(admin.ModelAdmin):
    list_display = ('truck', 'engine_oil_interval', 'engine_oil_last_km')
    autocomplete_fields = ['truck']
