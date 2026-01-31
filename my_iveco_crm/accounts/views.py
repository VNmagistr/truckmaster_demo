# accounts/views.py
from django.contrib.auth.models import User
from rest_framework import generics, viewsets, permissions
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import RegisterSerializer, MyTokenObtainPairSerializer, UserSerializer

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

# 🔥 ДОДАНО: ViewSet для списку користувачів
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Дозволяє отримувати список користувачів (для вибору механіка в замовленні).
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Можна фільтрувати по ролі (?role=mechanic), якщо буде потреба.
        Поки повертаємо всіх активних користувачів.
        """
        queryset = User.objects.filter(is_active=True)
        role = self.request.query_params.get('role', None)
        
        # Тут можна додати логіку фільтрації, наприклад:
        # if role == 'mechanic':
        #     return queryset.filter(groups__name='Mechanics')
            
        return queryset