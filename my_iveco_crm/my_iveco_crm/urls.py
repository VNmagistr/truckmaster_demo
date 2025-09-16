"""
URL configuration for my_iveco_crm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.routers import DefaultRouter
from clients.views import ClientViewSet, TruckViewSet, IvecoBaseModelViewSet
from clients.views import ClientViewSet, TruckViewSet, IvecoBaseModelViewSet
from orders.views import ServiceOrderViewSet, ServiceWorkViewSet, UsedPartViewSet, EmployeeViewSet, WorkGroupViewSet
from inventory.views import PartViewSet
from users.views import RegisterView

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'trucks', TruckViewSet)
router.register(r'base-models', IvecoBaseModelViewSet)
router.register(r'service-orders', ServiceOrderViewSet)
router.register(r'service-works', ServiceWorkViewSet)
router.register(r'used-parts', UsedPartViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'parts', PartViewSet)
router.register(r'work-groups', WorkGroupViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/register/', RegisterView.as_view(), name='register'),
]
