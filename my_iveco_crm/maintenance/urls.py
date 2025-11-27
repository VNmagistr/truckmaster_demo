# maintenance/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FluidChangeRecordViewSet,
    ServiceReminderViewSet,
    TruckFluidSpecViewSet
)

router = DefaultRouter()
router.register(r'fluid-changes', FluidChangeRecordViewSet, basename='fluid-change')
router.register(r'reminders', ServiceReminderViewSet, basename='reminder')
router.register(r'fluid-specs', TruckFluidSpecViewSet, basename='fluid-spec')

urlpatterns = [
    path('', include(router.urls)),
]