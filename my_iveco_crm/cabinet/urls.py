from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ClientTokenObtainPairView,
    ClientRegisterView,
    CabinetMeView,
    CabinetTrucksView,
    CabinetOrdersView,
    CabinetOrderDetailView,
)

urlpatterns = [
    # Auth
    path('token/', ClientTokenObtainPairView.as_view(), name='cabinet_token'),
    path('token/refresh/', TokenRefreshView.as_view(), name='cabinet_token_refresh'),
    path('register/', ClientRegisterView.as_view(), name='cabinet_register'),

    # Cabinet data
    path('me/', CabinetMeView.as_view(), name='cabinet_me'),
    path('trucks/', CabinetTrucksView.as_view(), name='cabinet_trucks'),
    path('orders/', CabinetOrdersView.as_view(), name='cabinet_orders'),
    path('orders/<int:pk>/', CabinetOrderDetailView.as_view(), name='cabinet_order_detail'),
]
