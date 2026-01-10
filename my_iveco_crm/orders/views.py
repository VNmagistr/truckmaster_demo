from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
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
    queryset = ServiceOrder.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceOrderListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceOrderWriteSerializer
        return ServiceOrderDetailSerializer
    
    def get_queryset(self):
        """
        ТИМЧАСОВО БЕЗ ФІЛЬТРА для дебагу
        """
        queryset = ServiceOrder.objects.select_related(
            'client', 
            'truck', 
            'truck__base_model'
        ).order_by('-created_at')
        
        # ЗАКОМЕНТОВАНО фільтр
        # show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'
        # if not show_deleted:
        #     queryset = queryset.filter(marked_for_deletion=False)
        
        # Глобальний пошук
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(client__name__icontains=search) |
                Q(truck__license_plate__icontains=search) |
                Q(truck__last_seven_vin__icontains=search) |
                Q(problem_description__icontains=search)
            )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Статистика для дашборду"""
        queryset = self.get_queryset()
        
        total = queryset.count()
        open_orders = queryset.filter(status='OPEN').count()
        in_progress = queryset.filter(status='IN_PROGRESS').count()
        closed = queryset.filter(status='CLOSED').count()
        
        return Response({
            'total': total,
            'open': open_orders,
            'in_progress': in_progress,
            'closed': closed,
        })

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