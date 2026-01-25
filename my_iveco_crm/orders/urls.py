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
router.register(r'orders', ServiceOrderViewSet)
router.register(r'service-works', ServiceWorkViewSet)
router.register(r'work-groups', WorkGroupViewSet)
router.register(r'work-prices', WorkPriceViewSet)
router.register(r'repair-photos', RepairPhotoViewSet)
router.register(r'maintenance-rules', MaintenanceRuleViewSet)
router.register(r'maintenance-logs', MaintenanceLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]