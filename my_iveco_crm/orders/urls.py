from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceOrderViewSet,
    ServiceWorkViewSet,
    WorkGroupViewSet,
    WorkPriceViewSet,
    RepairPhotoViewSet,
    MaintenanceRuleViewSet,
    MaintenanceLogViewSet
)

router = DefaultRouter()

# 1. Основний маршрут для нових функцій
router.register(r'orders', ServiceOrderViewSet, basename='orders')

# 2. ВАЖЛИВО: Маршрут для сумісності зі старим Дашбордом
# Саме його не вистачає для виправлення помилки 404
router.register(r'service-orders', ServiceOrderViewSet, basename='service-orders')

# 3. Інші маршрути
router.register(r'service-works', ServiceWorkViewSet)
router.register(r'work-groups', WorkGroupViewSet)
router.register(r'work-prices', WorkPriceViewSet)
router.register(r'repair-photos', RepairPhotoViewSet)
router.register(r'maintenance-rules', MaintenanceRuleViewSet)
router.register(r'maintenance-logs', MaintenanceLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]