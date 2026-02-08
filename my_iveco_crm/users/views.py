from django.contrib.auth.models import User
from rest_framework import generics, viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import RegisterSerializer, UserMeSerializer, ChangePasswordSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet для роботи з користувачами.
    """
    queryset = User.objects.all()
    serializer_class = UserMeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Звичайний юзер бачить тільки себе
        if self.request.user.is_superuser:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get', 'patch', 'delete'], url_path='me')
    def me(self, request):
        """
        Ендпоінт для профілю поточного користувача.
        GET: Отримати дані
        PATCH: Оновити дані
        DELETE: Деактивувати акаунт (soft delete)
        """
        user = request.user

        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data)

        elif request.method == 'PATCH':
            serializer = self.get_serializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            # "М'яке" видалення - просто деактивуємо
            user.is_active = False
            user.save()
            return Response(
                {"detail": "Акаунт деактивовано. Вихід із системи..."}, 
                status=status.HTTP_204_NO_CONTENT
            )

    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """Зміна паролю"""
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            if not user.check_password(serializer.data.get("old_password")):
                return Response(
                    {"old_password": ["Невірний старий пароль."]}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(serializer.data.get("new_password"))
            user.save()
            return Response({"detail": "Пароль успішно змінено"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)