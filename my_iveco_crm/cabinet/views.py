from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from clients.models import Truck
from orders.models import ServiceOrder

from .permissions import IsClientUser, ClientHasCabinetAccess, ClientEmailVerified
from .serializers import (
    ClientRegisterSerializer,
    ClientTokenObtainPairSerializer,
    CabinetClientSerializer,
    CabinetTruckSerializer,
    CabinetOrderListSerializer,
    CabinetOrderDetailSerializer,
)


class CabinetRateThrottle(AnonRateThrottle):
    rate = '10/minute'


# ── Auth ─────────────────────────────────────────────────────────────────────

class ClientTokenObtainPairView(TokenObtainPairView):
    """Логін для клієнта. Повертає 403, якщо user не є клієнтом."""
    serializer_class = ClientTokenObtainPairSerializer
    throttle_classes = [CabinetRateThrottle]


class ClientRegisterView(generics.CreateAPIView):
    """Самостійна реєстрація клієнта (ім'я + телефон + пароль)."""
    permission_classes = [AllowAny]
    throttle_classes = [CabinetRateThrottle]
    serializer_class = ClientRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Акаунт успішно створено.'}, status=status.HTTP_201_CREATED)


# ── Cabinet endpoints ─────────────────────────────────────────────────────────

class CabinetMeView(APIView):
    """Профіль поточного клієнта."""
    permission_classes = [IsClientUser, ClientHasCabinetAccess]

    def get(self, request):
        client = request.user.client_profile
        return Response(CabinetClientSerializer(client).data)


class CabinetTrucksView(generics.ListAPIView):
    """Список вантажівок клієнта."""
    permission_classes = [IsClientUser, ClientHasCabinetAccess, ClientEmailVerified]
    serializer_class = CabinetTruckSerializer
    pagination_class = None  # Клієнт бачить тільки свої авто — пагінація не потрібна

    def get_queryset(self):
        return Truck.objects.filter(
            client=self.request.user.client_profile,
            marked_for_deletion=False,
        ).select_related('base_model')


class CabinetOrdersView(generics.ListAPIView):
    """Список замовлень клієнта. Фільтр: ?truck=<id>"""
    permission_classes = [IsClientUser, ClientHasCabinetAccess, ClientEmailVerified]
    serializer_class = CabinetOrderListSerializer
    pagination_class = None  # Повертаємо всі замовлення клієнта без пагінації

    def get_queryset(self):
        client = self.request.user.client_profile
        qs = ServiceOrder.objects.filter(
            client=client,
            marked_for_deletion=False,
        ).select_related('truck', 'truck__base_model').order_by('-created_at')

        truck_id = self.request.query_params.get('truck')
        if truck_id:
            qs = qs.filter(truck_id=truck_id)
        return qs


class CabinetOrderDetailView(generics.RetrieveAPIView):
    """Деталі конкретного замовлення клієнта."""
    permission_classes = [IsClientUser, ClientHasCabinetAccess, ClientEmailVerified]
    serializer_class = CabinetOrderDetailSerializer

    def get_object(self):
        client = self.request.user.client_profile
        return get_object_or_404(
            ServiceOrder.objects.select_related('truck', 'truck__base_model')
            .prefetch_related('works', 'works__work', 'photos'),
            pk=self.kwargs['pk'],
            client=client,
            marked_for_deletion=False,
        )


# ── Email verification ────────────────────────────────────────────────────────

class VerifyEmailView(APIView):
    """Підтвердження email за токеном із листа."""
    permission_classes = [AllowAny]

    def get(self, request):
        from .models import EmailVerification

        token = request.query_params.get('token')
        if not token:
            return Response({'detail': 'Токен відсутній.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            verification = EmailVerification.objects.select_related('client').get(token=token)
        except EmailVerification.DoesNotExist:
            return Response({'detail': 'Недійсний токен.'}, status=status.HTTP_400_BAD_REQUEST)

        if not verification.is_valid():
            return Response(
                {'detail': 'Термін дії токена закінчився або він вже використаний.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client = verification.client
        client.email = verification.email
        client.email_verified = True
        client.save(update_fields=['email', 'email_verified'])

        verification.is_used = True
        verification.save(update_fields=['is_used'])

        return Response({'detail': 'Email успішно підтверджено. Тепер ви маєте повний доступ.'})


class ResendVerificationEmailView(APIView):
    """Повторне надсилання листа з підтвердженням."""
    permission_classes = [IsClientUser]
    throttle_classes = [CabinetRateThrottle]

    def post(self, request):
        from .email_utils import send_verification_email

        client = request.user.client_profile

        if client.email_verified:
            return Response({'detail': 'Email вже підтверджено.'}, status=status.HTTP_400_BAD_REQUEST)

        if not client.email:
            return Response(
                {'detail': 'Email адреса не встановлена. Зверніться до менеджера.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            send_verification_email(client, client.email)
        except Exception:
            return Response(
                {'detail': 'Помилка надсилання листа. Спробуйте пізніше.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({'detail': f'Лист з підтвердженням надіслано на {client.email}.'})
