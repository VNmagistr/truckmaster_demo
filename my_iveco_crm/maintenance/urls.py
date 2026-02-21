# maintenance/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceTypeViewSet,
    ServiceReminderViewSet,
    CheckRegulationsView,
)

router = DefaultRouter()
router.register(r'service-types', ServiceTypeViewSet, basename='service-type')
router.register(r'reminders', ServiceReminderViewSet, basename='reminder')

urlpatterns = [
    path('', include(router.urls)),
    path('check-regulations/', CheckRegulationsView.as_view(), name='check-regulations'),
]