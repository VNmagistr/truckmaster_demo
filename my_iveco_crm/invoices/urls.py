from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, InvoiceItemViewSet, DriverPickupLogViewSet, track_nova_poshta

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'invoice-items', InvoiceItemViewSet, basename='invoice-item')
router.register(r'driver-pickups', DriverPickupLogViewSet, basename='driver-pickup')

urlpatterns = [
    path('', include(router.urls)),
    path('nova-poshta/track/<str:number>/', track_nova_poshta, name='nova-poshta-track'),
]
