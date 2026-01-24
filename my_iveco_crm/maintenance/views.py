# maintenance/views.py

from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q

# Імпорти моделей з поточної програми
from .models import FluidChangeRecord, ServiceReminder, TruckFluidSpec, ServiceType
# Імпорти моделей з інших програм (для аналізу)
from clients.models import Truck
from orders.models import MaintenanceRule, MaintenanceLog  # Ті самі правила, що ми створили раніше

from .serializers import (
    FluidChangeRecordSerializer,
    ServiceReminderSerializer,
    TruckFluidSpecSerializer,
    ServiceTypeSerializer
)


class ServiceTypeViewSet(viewsets.ModelViewSet):
    """API для типів технічного обслуговування"""
    queryset = ServiceType.objects.filter(is_active=True).all()
    serializer_class = ServiceTypeSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['sort_order', 'name']
    ordering = ['sort_order', 'name']


class FluidChangeRecordViewSet(viewsets.ModelViewSet):
    """API для історії замін рідин"""
    queryset = FluidChangeRecord.objects.select_related(
        'truck', 'subcategory', 'product', 'service_order', 'created_by'
    ).all()
    serializer_class = FluidChangeRecordSerializer
    permission_classes = [IsAuthenticated]
    
    filterset_fields = ['truck', 'subcategory', 'product']
    search_fields = ['truck__license_plate', 'notes']
    ordering_fields = ['performed_at', 'mileage', 'created_at']
    ordering = ['-performed_at']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_truck(self, request):
        truck_id = request.query_params.get('truck_id')
        if not truck_id:
            return Response({'error': 'truck_id is required'}, status=400)
        records = self.queryset.filter(truck_id=truck_id)
        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming_changes(self, request):
        today = timezone.now().date()
        upcoming_date = today + timezone.timedelta(days=30)
        records = self.queryset.filter(
            Q(next_change_date__lte=upcoming_date, next_change_date__gte=today) |
            Q(next_change_date__isnull=True, next_change_mileage__isnull=False)
        ).order_by('next_change_date', 'next_change_mileage')
        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data)


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


class TruckFluidSpecViewSet(viewsets.ModelViewSet):
    """API для специфікацій рідин вантажівок"""
    queryset = TruckFluidSpec.objects.select_related(
        'truck', 'subcategory', 'recommended_product'
    ).prefetch_related('alternative_products').all()
    serializer_class = TruckFluidSpecSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['truck', 'subcategory']
    search_fields = ['truck__license_plate', 'notes']
    
    @action(detail=False, methods=['get'])
    def by_truck(self, request):
        truck_id = request.query_params.get('truck_id')
        if not truck_id:
            return Response({'error': 'truck_id is required'}, status=400)
        specs = self.queryset.filter(truck_id=truck_id)
        serializer = self.get_serializer(specs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        truck_id = request.query_params.get('truck_id')
        subcategory_id = request.query_params.get('subcategory_id')
        if not truck_id:
            return Response({'error': 'truck_id is required'}, status=400)
        specs = self.queryset.filter(truck_id=truck_id)
        if subcategory_id:
            specs = specs.filter(subcategory_id=subcategory_id)
        serializer = self.get_serializer(specs, many=True)
        return Response(serializer.data)


# --- НОВИЙ КЛАС ДЛЯ АНАЛІЗУ ПРОБІГУ ---

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

        # 2. Перевірка ПРАВИЛ РЕГЛАМЕНТУ (MaintenanceRule з orders/models.py)
        # Це перевірка "на льоту"
        rules = MaintenanceRule.objects.all() # Можна додати фільтр по моделі авто

        for rule in rules:
            # Шукаємо останній запис в журналі
            last_log = MaintenanceLog.objects.filter(truck=truck, rule=rule).order_by('-date_performed').first()
            
            # Тут спрощена логіка: якщо ніколи не робили АБО пройшло достатньо км
            # В ідеалі треба зберігати "пробіг останнього ТО" в MaintenanceLog
            
            should_recommend = False
            
            if not last_log:
                # Якщо ніколи не робили - рекомендуємо (для демо)
                # В реальності можемо перевіряти current_mileage > rule.km_interval
                if current_mileage >= rule.km_interval:
                    should_recommend = True
            else:
                # Тут треба знати пробіг на момент останнього ТО. 
                # Припустимо, ми додамо поле mileage в MaintenanceLog пізніше.
                # Поки що просто перевіряємо, чи кратен пробіг інтервалу (груба перевірка)
                pass 

            # ДЕМО-ЛОГІКА (Щоб ти побачив результат):
            # Якщо пробіг ділиться на інтервал (з похибкою 1000 км)
            remainder = current_mileage % rule.km_interval
            if remainder > (rule.km_interval - 1000) or remainder < 1000:
                 recommendations.append({
                    'id': f'rule_{rule.id}',
                    'title': rule.name,
                    'description': f"Регламент: кожні {rule.km_interval} км",
                    'priority': 'high' if remainder < 500 else 'medium',
                    'source': 'rule'
                })

        return Response({'recommendations': recommendations})