# maintenance/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q

from .models import FluidChangeRecord, ServiceReminder, TruckFluidSpec
from .serializers import (
    FluidChangeRecordSerializer,
    ServiceReminderSerializer,
    TruckFluidSpecSerializer
)


class FluidChangeRecordViewSet(viewsets.ModelViewSet):
    """
    API для історії замін рідин
    """
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
        """Отримати історію замін для конкретної вантажівки"""
        truck_id = request.query_params.get('truck_id')
        if not truck_id:
            return Response(
                {'error': 'truck_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        records = self.queryset.filter(truck_id=truck_id)
        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming_changes(self, request):
        """Вантажівки, яким скоро потрібна заміна"""
        # Отримуємо записи де next_change_mileage близький до поточного пробігу
        # або next_change_date в найближчі 30 днів
        today = timezone.now().date()
        upcoming_date = today + timezone.timedelta(days=30)
        
        records = self.queryset.filter(
            Q(next_change_date__lte=upcoming_date, next_change_date__gte=today) |
            Q(next_change_date__isnull=True, next_change_mileage__isnull=False)
        ).order_by('next_change_date', 'next_change_mileage')
        
        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data)


class ServiceReminderViewSet(viewsets.ModelViewSet):
    """
    API для нагадувань про ТО
    """
    queryset = ServiceReminder.objects.select_related(
        'truck', 'subcategory', 'completed_order'
    ).all()
    serializer_class = ServiceReminderSerializer
    permission_classes = [IsAuthenticated]
    
    filterset_fields = ['truck', 'status', 'priority', 'subcategory']
    search_fields = ['truck__license_plate', 'title', 'description']
    ordering_fields = ['target_date', 'target_mileage', 'priority', 'status']
    ordering = ['status', 'target_date']
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Тільки активні нагадування"""
        reminders = self.queryset.filter(
            status__in=['pending', 'notified', 'overdue']
        )
        serializer = self.get_serializer(reminders, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Прострочені нагадування"""
        reminders = self.queryset.filter(status='overdue')
        serializer = self.get_serializer(reminders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Позначити як виконано"""
        reminder = self.get_object()
        order_id = request.data.get('order_id')
        
        reminder.status = 'completed'
        reminder.completed_at = timezone.now()
        if order_id:
            reminder.completed_order_id = order_id
        reminder.save()
        
        serializer = self.get_serializer(reminder)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Відхилити нагадування"""
        reminder = self.get_object()
        reminder.status = 'dismissed'
        reminder.save()
        
        serializer = self.get_serializer(reminder)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_truck(self, request):
        """Нагадування для конкретної вантажівки"""
        truck_id = request.query_params.get('truck_id')
        if not truck_id:
            return Response(
                {'error': 'truck_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reminders = self.queryset.filter(truck_id=truck_id)
        serializer = self.get_serializer(reminders, many=True)
        return Response(serializer.data)


class TruckFluidSpecViewSet(viewsets.ModelViewSet):
    """
    API для специфікацій рідин вантажівок
    """
    queryset = TruckFluidSpec.objects.select_related(
        'truck', 'subcategory', 'recommended_product'
    ).prefetch_related('alternative_products').all()
    serializer_class = TruckFluidSpecSerializer
    permission_classes = [IsAuthenticated]
    
    filterset_fields = ['truck', 'subcategory']
    search_fields = ['truck__license_plate', 'notes']
    
    @action(detail=False, methods=['get'])
    def by_truck(self, request):
        """Специфікації для конкретної вантажівки"""
        truck_id = request.query_params.get('truck_id')
        if not truck_id:
            return Response(
                {'error': 'truck_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        specs = self.queryset.filter(truck_id=truck_id)
        serializer = self.get_serializer(specs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """Рекомендації по рідинах для вантажівки"""
        truck_id = request.query_params.get('truck_id')
        subcategory_id = request.query_params.get('subcategory_id')
        
        if not truck_id:
            return Response(
                {'error': 'truck_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        specs = self.queryset.filter(truck_id=truck_id)
        if subcategory_id:
            specs = specs.filter(subcategory_id=subcategory_id)
        
        serializer = self.get_serializer(specs, many=True)
        return Response(serializer.data)