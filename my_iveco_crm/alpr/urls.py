from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import alpr_event, IgnoredVehicleViewSet, VehicleArrivalViewSet

router = DefaultRouter()
router.register('alpr/ignored', IgnoredVehicleViewSet, basename='alpr-ignored')
router.register('alpr/arrivals', VehicleArrivalViewSet, basename='alpr-arrivals')

urlpatterns = [
    path('alpr/event/', alpr_event, name='alpr-event'),
    path('', include(router.urls)),
]
