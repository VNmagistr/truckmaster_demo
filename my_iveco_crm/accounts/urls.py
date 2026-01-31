# accounts/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, MyTokenObtainPairView, UserViewSet
from rest_framework_simplejwt.views import TokenRefreshView

# 🔥 Створюємо роутер для ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    
    # 🔥 Підключаємо маршрути роутера (це активує /users/)
    path('', include(router.urls)),
]