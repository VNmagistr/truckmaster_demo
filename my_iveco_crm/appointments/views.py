from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Appointment
from .serializers import AppointmentSerializer


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related('client', 'created_by', 'converted_to_order')
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if start := params.get('start'):
            qs = qs.filter(scheduled_dt__gte=start)
        if end := params.get('end'):
            qs = qs.filter(scheduled_dt__lte=end)
        if s := params.get('status'):
            qs = qs.filter(status=s)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        appt = self.get_object()
        if appt.status not in ('pending',):
            return Response({'detail': 'Можна підтвердити лише запис зі статусом "Очікує"'},
                            status=status.HTTP_400_BAD_REQUEST)
        appt.status = 'confirmed'
        appt.save()
        return Response(AppointmentSerializer(appt).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        appt = self.get_object()
        if appt.status in ('completed', 'cancelled'):
            return Response({'detail': 'Цей запис вже завершено або скасовано'},
                            status=status.HTTP_400_BAD_REQUEST)
        appt.status = 'cancelled'
        appt.save()
        return Response(AppointmentSerializer(appt).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        appt = self.get_object()
        appt.status = 'completed'
        appt.save()
        return Response(AppointmentSerializer(appt).data)
