# urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from clients.views import ClientViewSet, TruckViewSet, IvecoBaseModelViewSet
# 1. Оновлюємо імпорти з orders.views
from orders.views import (
    ServiceOrderViewSet, 
    ServiceWorkViewSet, 
    UsedPartViewSet, 
    EmployeeViewSet, 
    WorkCategoryViewSet, # <-- Замість WorkGroupViewSet
    RepairPhotoViewSet
)
from inventory.views import PartViewSet
from accounts.views import RegisterView, MyTokenObtainPairView

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'trucks', TruckViewSet)
router.register(r'base-models', IvecoBaseModelViewSet)
router.register(r'orders', ServiceOrderViewSet, basename='serviceorder')
router.register(r'service-works', ServiceWorkViewSet)
router.register(r'used-parts', UsedPartViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'parts', PartViewSet)
router.register(r'repair-photos', RepairPhotoViewSet)

# 2. Реєструємо новий ендпоінт для категорій робіт
router.register(r'work-categories', WorkCategoryViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/register/', RegisterView.as_view(), name='register'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)