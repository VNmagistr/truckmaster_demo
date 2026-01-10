from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import (
    ServiceOrder, ServiceWork, Employee, WorkGroup, WorkPrice, 
    RepairPhoto, MaintenanceRule, MaintenanceLog
)
from .serializers import (
    ServiceOrderListSerializer,
    ServiceOrderDetailSerializer,
    ServiceOrderWriteSerializer,
    ServiceWorkSerializer,
    ServiceWorkWriteSerializer,
    EmployeeSerializer,
    WorkGroupSerializer,
    WorkPriceSerializer,
    RepairPhotoSerializer,
    MaintenanceRuleSerializer,
    MaintenanceLogSerializer
)


class IsAuthenticated(permissions.IsAuthenticated):
    pass


class ServiceOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Фільтруємо видалені замовлення за замовчуванням"""
        queryset = ServiceOrder.objects.all()
        
        # Якщо явно не запитано marked_for_deletion, показуємо тільки активні
        if 'marked_for_deletion' not in self.request.query_params:
            queryset = queryset.filter(marked_for_deletion=False)
        
        # Завжди використовуємо select_related для оптимізації
        queryset = queryset.select_related('client', 'truck', 'truck__base_model')
        
        # Підтримка пошуку
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(client__name__icontains=search) |
                Q(truck__license_plate__icontains=search) |
                Q(truck__last_seven_vin__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceOrderListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceOrderWriteSerializer
        return ServiceOrderDetailSerializer
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Останні 10 замовлень"""
        orders = self.get_queryset()[:10]
        serializer = ServiceOrderListSerializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Статистика для дашборду"""
        queryset = self.get_queryset()
        
        # Підрахунки по статусах
        stats = {
            'total': queryset.count(),
            'open': queryset.filter(status='OPEN').count(),
            'in_progress': queryset.filter(status='IN_PROGRESS').count(),
            'closed': queryset.filter(status='CLOSED').count(),
            'today': queryset.filter(created_at__date=timezone.now().date()).count(),
            'this_week': queryset.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
        }
        
        return Response(stats)


class ServiceWorkViewSet(viewsets.ModelViewSet):
    queryset = ServiceWork.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceWorkWriteSerializer
        return ServiceWorkSerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]


class WorkGroupViewSet(viewsets.ModelViewSet):
    queryset = WorkGroup.objects.all()
    serializer_class = WorkGroupSerializer
    permission_classes = [IsAuthenticated]


class WorkPriceViewSet(viewsets.ModelViewSet):
    queryset = WorkPrice.objects.all()
    serializer_class = WorkPriceSerializer
    permission_classes = [IsAuthenticated]


class RepairPhotoViewSet(viewsets.ModelViewSet):
    queryset = RepairPhoto.objects.all()
    serializer_class = RepairPhotoSerializer
    permission_classes = [IsAuthenticated]


class MaintenanceRuleViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRule.objects.all()
    serializer_class = MaintenanceRuleSerializer
    permission_classes = [IsAuthenticated]


class MaintenanceLogViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceLog.objects.all()
    serializer_class = MaintenanceLogSerializer
    permission_classes = [IsAuthenticated]
    