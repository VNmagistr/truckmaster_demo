# maintenance/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceTypeViewSet,
    FluidChangeRecordViewSet,
    ServiceReminderViewSet,
    TruckFluidSpecViewSet,
    CheckRegulationsView  # <-- 1. Додаємо імпорт
)

router = DefaultRouter()
router.register(r'service-types', ServiceTypeViewSet, basename='service-type')
router.register(r'fluid-changes', FluidChangeRecordViewSet, basename='fluid-change')
router.register(r'reminders', ServiceReminderViewSet, basename='reminder')
router.register(r'fluid-specs', TruckFluidSpecViewSet, basename='fluid-spec')

urlpatterns = [
    path('', include(router.urls)),
    path('check-regulations/', CheckRegulationsView.as_view(), name='check-regulations'),
]