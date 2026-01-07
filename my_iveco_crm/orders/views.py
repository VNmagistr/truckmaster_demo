from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
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
from django_filters.rest_framework import DjangoFilterBackend

class IsAuthenticated(permissions.IsAuthenticated):
    pass

class ServiceOrderViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrder.objects.select_related('client', 'truck', 'truck__base_model').all().order_by('-created_at')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'order_number',
        'truck__full_vin',
        'truck__license_plate',
        'client__name',
    ]
    ordering_fields = ['created_at', 'order_number', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceOrderListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceOrderWriteSerializer
        return ServiceOrderDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        global_search = self.request.query_params.get('global_search', None)
        
        if global_search:
            queryset = queryset.filter(
                Q(order_number__icontains=global_search) |
                Q(truck__full_vin__icontains=global_search) |
                Q(truck__license_plate__icontains=global_search) |
                Q(client__name__icontains=global_search)
            )
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def previous_maintenance(self, request, pk=None):
        """Отримати попередні ТО для вантажівки з цього наряду"""
        order = self.get_object()
        if not order.truck:
            return Response({'results': []})
        
        previous_orders = ServiceOrder.objects.filter(
            truck=order.truck,
            status='CLOSED'
        ).exclude(id=order.id).order_by('-created_at')[:5]
        
        result = []
        for prev_order in previous_orders:
            works = prev_order.works.filter(
                Q(work__name__icontains='ТО') |
                Q(work__name__icontains='олив') |
                Q(work__name__icontains='фільтр') |
                Q(work__work_group__name__icontains='ТО')
            ).select_related('work', 'work__work_group')
            
            if works.exists():
                work_data = {
                    'order_id': prev_order.id,
                    'order_number': prev_order.order_number,
                    'date': prev_order.created_at,
                    'works': []
                }
                
                for work in works:
                    used_parts = work.used_parts.all().select_related('part')
                    parts_list = [
                        {
                            'part_id': up.part.id,
                            'part_name': up.part.name,
                            'quantity': up.quantity
                        }
                        for up in used_parts
                    ]
                    
                    work_data['works'].append({
                        'work_id': work.work.id if work.work else None,
                        'work_name': work.work.name if work.work else 'Інше',
                        'parts': parts_list
                    })
                
                if work_data['works']:
                    result.append(work_data)
        
        return Response({'results': result})
    
    @action(detail=True, methods=['post'])
    def mark_for_deletion(self, request, pk=None):
        """Позначити наряд на видалення"""
        order = self.get_object()
        reason = request.data.get('reason', '')
        
        order.marked_for_deletion = True
        order.marked_for_deletion_by = request.user
        order.marked_for_deletion_at = timezone.now()
        order.deletion_reason = reason
        order.save()
        
        return Response({
            'status': 'success',
            'message': 'Наряд-замовлення позначено на видалення'
        })
    
    @action(detail=True, methods=['post'])
    def unmark_for_deletion(self, request, pk=None):
        """Зняти позначку на видалення"""
        order = self.get_object()
        
        order.marked_for_deletion = False
        order.marked_for_deletion_by = None
        order.marked_for_deletion_at = None
        order.deletion_reason = ''
        order.save()
        
        return Response({
            'status': 'success',
            'message': 'Позначку на видалення знято'
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
