import logging
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from clients.models import Truck
from appointments.models import Appointment

from .models import IgnoredVehicle, VehicleArrival, normalize_plate
from .serializers import IgnoredVehicleSerializer, VehicleArrivalSerializer, AlprEventInputSerializer
from .permissions import AlprApiKeyPermission
from .notifications import send_staff_telegram

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AlprApiKeyPermission])
def alpr_event(request):
    """
    Endpoint для ALPR-скрипта/камери.
    Приймає розпізнаний номер, перевіряє ігнор-лист, шукає клієнта/авто/запис,
    надсилає сповіщення персоналу.

    Auth: заголовок X-ALPR-Key: <ALPR_API_KEY з .env>
    """
    serializer = AlprEventInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    raw_plate = serializer.validated_data['license_plate']
    plate = normalize_plate(raw_plate)
    camera_id = serializer.validated_data.get('camera_id', '')
    confidence = serializer.validated_data.get('confidence')

    # 1. Перевірка списку ігнору
    ignored_entry = IgnoredVehicle.objects.filter(license_plate=plate, is_active=True).first()
    if ignored_entry:
        VehicleArrival.objects.create(
            license_plate=plate,
            camera_id=camera_id,
            confidence=confidence,
            ignored=True,
            ignore_reason=ignored_entry.get_reason_type_display(),
            notified=False,
        )
        return Response({'status': 'ignored', 'reason': ignored_entry.get_reason_type_display()})

    # 2. Пошук автомобіля та клієнта
    truck = Truck.objects.select_related('client').filter(license_plate=plate).first()
    client = truck.client if truck else None

    # 3. Пошук запису на СТО на сьогодні
    today = timezone.localdate()
    appointment = (
        Appointment.objects
        .filter(license_plate=plate, scheduled_dt__date=today)
        .exclude(status__in=['cancelled', 'completed', 'no_show'])
        .order_by('scheduled_dt')
        .first()
    )

    # 4. Збереження події
    arrival = VehicleArrival.objects.create(
        license_plate=plate,
        camera_id=camera_id,
        confidence=confidence,
        truck=truck,
        client=client,
        appointment=appointment,
        ignored=False,
    )

    # 5. Telegram-сповіщення персоналу
    try:
        send_staff_telegram(arrival)
        arrival.notified = True
        arrival.save(update_fields=['notified'])
    except Exception as e:
        logger.error(f"ALPR notify error: {e}")

    return Response({
        'status': 'ok',
        'arrival_id': arrival.id,
        'license_plate': plate,
        'client': client.name if client else None,
        'truck': str(truck) if truck else None,
        'appointment_id': appointment.id if appointment else None,
    })


class IgnoredVehicleViewSet(viewsets.ModelViewSet):
    """CRUD для списку ігнорованих автомобілів. Доступ — авторизований персонал."""
    queryset = IgnoredVehicle.objects.select_related('added_by').order_by('reason_type', 'license_plate')
    serializer_class = IgnoredVehicleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)


class VehicleArrivalViewSet(viewsets.ReadOnlyModelViewSet):
    """Журнал заїздів — тільки читання. Фільтри: ?date=2026-03-17 ?ignored=true."""
    queryset = VehicleArrival.objects.select_related('truck', 'client', 'appointment').order_by('-detected_at')
    serializer_class = VehicleArrivalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if date := params.get('date'):
            qs = qs.filter(detected_at__date=date)
        if ignored := params.get('ignored'):
            qs = qs.filter(ignored=ignored.lower() in ('true', '1', 'yes'))
        if plate := params.get('plate'):
            qs = qs.filter(license_plate__icontains=plate)
        return qs
