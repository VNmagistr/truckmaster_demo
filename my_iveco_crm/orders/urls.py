from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceOrderViewSet,
    ServiceWorkViewSet,
    WorkGroupViewSet,
    WorkPriceViewSet,
    RepairPhotoViewSet,
    MaintenanceRuleViewSet,
    MaintenanceLogViewSet,
    MaintenanceKitViewSet,
    MaintenanceKitFilterViewSet,
    TruckMaintenanceIntervalsViewSet,
    MaintenanceIntervalsTemplateViewSet,
    BaseMaintenanceKitViewSet,
)

router = DefaultRouter()

# Основний маршрут для замовлень
router.register(r'orders', ServiceOrderViewSet, basename='orders')

# Маршрут для сумісності зі старим кодом
router.register(r'service-orders', ServiceOrderViewSet, basename='service-orders')

# Інші маршрути
router.register(r'service-works', ServiceWorkViewSet)
router.register(r'work-groups', WorkGroupViewSet)
router.register(r'work-prices', WorkPriceViewSet)
router.register(r'repair-photos', RepairPhotoViewSet)
router.register(r'maintenance-rules', MaintenanceRuleViewSet)
router.register(r'maintenance-logs', MaintenanceLogViewSet)
router.register(r'maintenance-kits', MaintenanceKitViewSet, basename='maintenance-kits')
router.register(r'maintenance-kit-filters', MaintenanceKitFilterViewSet, basename='maintenance-kit-filters')
router.register(r'maintenance-intervals', TruckMaintenanceIntervalsViewSet, basename='maintenance-intervals')
router.register(r'maintenance-templates', MaintenanceIntervalsTemplateViewSet, basename='maintenance-templates')
router.register(r'base-maintenance-kits', BaseMaintenanceKitViewSet, basename='base-maintenance-kits')

urlpatterns = [
    path('', include(router.urls)),
]