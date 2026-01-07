from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceOrderViewSet,
    ServiceWorkViewSet,
    EmployeeViewSet,
    WorkGroupViewSet,
    WorkPriceViewSet,
    RepairPhotoViewSet,
    MaintenanceRuleViewSet,
    MaintenanceLogViewSet
)

# Створюємо роутер для автоматичної генерації URL
router = DefaultRouter()
router.register(r'service-orders', ServiceOrderViewSet, basename='serviceorder')
router.register(r'service-works', ServiceWorkViewSet, basename='servicework')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'work-groups', WorkGroupViewSet, basename='workgroup')
router.register(r'work-prices', WorkPriceViewSet, basename='workprice')
router.register(r'repair-photos', RepairPhotoViewSet, basename='repairphoto')
router.register(r'maintenance-rules', MaintenanceRuleViewSet, basename='maintenancerule')
router.register(r'maintenance-logs', MaintenanceLogViewSet, basename='maintenancelog')

# Додаємо алієс /orders/ для зворотної сумісності з фронтендом
router.register(r'orders', ServiceOrderViewSet, basename='order')

# Головний список URL-адрес
urlpatterns = [
    path('', include(router.urls)),
]