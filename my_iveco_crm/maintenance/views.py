# maintenance/views.py

from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404

# Імпорти моделей з поточної програми
from .models import ServiceReminder, ServiceType
# Імпорти моделей з інших програм (для аналізу)
from clients.models import Truck
from orders.models import MaintenanceRule, MaintenanceLog, TruckMaintenanceIntervals

from .serializers import (
    ServiceReminderSerializer,
    ServiceTypeSerializer,
)


class ServiceTypeViewSet(viewsets.ModelViewSet):
    """API для типів технічного обслуговування"""
    queryset = ServiceType.objects.filter(is_active=True).all()
    serializer_class = ServiceTypeSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['sort_order', 'name']
    ordering = ['sort_order', 'name']


class ServiceReminderViewSet(viewsets.ModelViewSet):
    """API для нагадувань про ТО"""
    queryset = ServiceReminder.objects.select_related(
        'truck', 'service_type', 'completed_order'
    ).all()
    serializer_class = ServiceReminderSerializer
    permission_classes = [IsAuthenticated]
    
    filterset_fields = ['truck', 'status', 'priority', 'service_type']
    search_fields = ['truck__license_plate', 'title', 'description']
    ordering_fields = ['target_date', 'target_mileage', 'priority', 'status']
    ordering = ['status', 'target_date']
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        reminders = self.queryset.filter(status__in=['pending', 'notified', 'overdue'])
        serializer = self.get_serializer(reminders, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        reminders = self.queryset.filter(status='overdue')
        serializer = self.get_serializer(reminders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        reminder = self.get_object()
        order_id = request.data.get('order_id')
        reminder.status = 'completed'
        reminder.completed_at = timezone.now()
        if order_id:
            reminder.completed_order_id = order_id
        reminder.save()
        return Response(self.get_serializer(reminder).data)
    
    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        reminder = self.get_object()
        reminder.status = 'dismissed'
        reminder.save()
        return Response(self.get_serializer(reminder).data)
    
    @action(detail=False, methods=['get'])
    def by_truck(self, request):
        truck_id = request.query_params.get('truck_id')
        if not truck_id:
            return Response({'error': 'truck_id is required'}, status=400)
        reminders = self.queryset.filter(truck_id=truck_id)
        serializer = self.get_serializer(reminders, many=True)
        return Response(serializer.data)


# --- КЛАС ДЛЯ АНАЛІЗУ ПРОБІГУ ---

class CheckRegulationsView(views.APIView):
    """
    Аналізує пробіг і повертає список рекомендованих робіт.
    Працює на стику MaintenanceRule (з orders) та ServiceReminder (з maintenance).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        truck_id = request.query_params.get('truck_id')
        mileage_str = request.query_params.get('mileage')

        if not truck_id or not mileage_str:
            return Response({'error': 'Вкажіть truck_id та mileage'}, status=400)

        try:
            current_mileage = int(mileage_str)
            truck = get_object_or_404(Truck, id=truck_id)
        except ValueError:
            return Response({'error': 'Пробіг має бути числом'}, status=400)

        recommendations = []

        # 1. Перевірка існуючих НАГАДУВАНЬ (ServiceReminder)
        # Це ті, що вже були створені системою раніше
        reminders = ServiceReminder.objects.filter(
            truck=truck,
            status__in=['pending', 'overdue', 'notified']
        )
        for reminder in reminders:
            # Якщо пробіг підійшов або дата настала
            is_mileage_due = reminder.target_mileage and current_mileage >= (reminder.target_mileage - 1000)
            is_date_due = reminder.target_date and reminder.target_date <= timezone.now().date()
            
            if is_mileage_due or is_date_due:
                recommendations.append({
                    'id': f'reminder_{reminder.id}',
                    'title': reminder.title,
                    'description': reminder.description or f"Планове ТО (нагадування від {reminder.created_at.date()})",
                    'priority': 'high' if reminder.status == 'overdue' else 'medium',
                    'source': 'reminder'
                })

        # 2. Перевірка регламентних робіт на основі TruckMaintenanceIntervals
        try:
            intervals = truck.maintenance_intervals
        except TruckMaintenanceIntervals.DoesNotExist:
            intervals = None

        if intervals:
            INTERVAL_CHECKS = [
                ('engine_oil', 'Заміна оливи в двигуні'),
                ('gearbox_oil', 'Заміна оливи в КПП'),
                ('auto_gearbox_oil', 'Заміна оливи в АКПП'),
                ('rear_axle_oil', 'Заміна оливи в задньому мості'),
                ('belts', 'Заміна ремнів/роликів'),
                ('chains', 'Заміна ланцюгів ГРМ'),
            ]
            for key, label in INTERVAL_CHECKS:
                interval = getattr(intervals, f'{key}_interval', None)
                last_km = getattr(intervals, f'{key}_last_km', None)
                if not interval or not last_km:
                    continue
                remaining = last_km + interval - current_mileage
                if remaining <= 1000:
                    priority = 'high' if remaining <= 0 else 'medium'
                    recommendations.append({
                        'id': f'interval_{key}',
                        'title': label,
                        'description': f"Регламент: кожні {interval:,} км, залишок: {remaining:,} км",
                        'priority': priority,
                        'source': 'interval',
                    })

        return Response({'recommendations': recommendations})