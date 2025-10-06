"""
URL configuration for my_iveco_crm project.
...
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from clients.views import ClientViewSet, TruckViewSet, IvecoBaseModelViewSet
# Виправлено дублювання імпорту
from orders.views import ServiceOrderViewSet, ServiceWorkViewSet, UsedPartViewSet, EmployeeViewSet, WorkGroupViewSet, RepairPhotoViewSet
from inventory.views import PartViewSet
from accounts.views import RegisterView, MyTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'trucks', TruckViewSet)
router.register(r'base-models', IvecoBaseModelViewSet)
# У ServiceOrderViewSet ми використовуємо 'service-orders', а не 'orders', як на фронтенді. Давайте виправимо і це для консистентності.
router.register(r'orders', ServiceOrderViewSet, basename='serviceorder') # <-- ЗМІНЕНО
router.register(r'service-works', ServiceWorkViewSet)
router.register(r'used-parts', UsedPartViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'parts', PartViewSet)
router.register(r'workgroups', WorkGroupViewSet) # <-- ОСНОВНЕ ВИПРАВЛЕННЯ
router.register(r'repair-photos', RepairPhotoViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/register/', RegisterView.as_view(), name='register'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)