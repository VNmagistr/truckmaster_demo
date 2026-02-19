from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    ServiceOrder, ServiceWork, WorkGroup, WorkPrice, 
    RepairPhoto, MaintenanceRule, MaintenanceLog, MaintenanceKit
)
from clients.models import Truck
from inventory.models import UsedPart
from .serializers import (
    ServiceOrderListSerializer,
    ServiceOrderDetailSerializer,
    ServiceOrderWriteSerializer,
    ServiceWorkSerializer,
    ServiceWorkWriteSerializer,
    WorkGroupSerializer,
    WorkPriceSerializer,
    RepairPhotoSerializer,
    MaintenanceRuleSerializer,
    MaintenanceLogSerializer,
    MaintenanceKitSerializer,
    UsedPartSerializer
)


class ServiceOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet для роботи з нарядами-замовленнями.
    Виправлено: додано truck__client до select_related для оптимізації запитів.
    """
    queryset = ServiceOrder.objects.select_related(
        'client', 
        'truck',
        'truck__client',  # Додано для оптимізації запитів до клієнта вантажівки
        'marked_for_deletion_by'
    ).all().order_by('-created_at')
    
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    search_fields = [
        'order_number',
        'truck__license_plate', 
        'client__name',
    ]
    filterset_fields = ['status', 'client', 'truck', 'marked_for_deletion']
    ordering_fields = ['created_at', 'order_number', 'status']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceOrderListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceOrderWriteSerializer
        return ServiceOrderDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                'works', 'works__work', 'works__mechanic', 
                'works__used_parts', 'works__used_parts__part', 'photos'
            )
            return queryset
            
        if self.action == 'list':
            marked_param = self.request.query_params.get('marked_for_deletion')
            if str(marked_param).lower() != 'true':
                queryset = queryset.filter(marked_for_deletion=False)
            
        global_search = self.request.query_params.get('global_search', None)
        if global_search:
            queryset = queryset.filter(
                Q(order_number__icontains=global_search) |
                Q(truck__license_plate__icontains=global_search) |
                Q(client__name__icontains=global_search)
            )
        return queryset

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Фізичне видалення заборонено. Використовуйте позначення на видалення."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(detail=False, methods=['get'], url_path='search-truck')
    def search_truck(self, request):
        """Пошук вантажівки за номерним знаком."""
        plate_query = request.query_params.get('plate', '').strip()
        if len(plate_query) < 2:
            return Response({'results': []}, status=status.HTTP_200_OK)

        trucks = Truck.objects.select_related('client').filter(
            license_plate__icontains=plate_query
        )[:10]

        results = []
        for truck in trucks:
            results.append({
                'id': truck.id,
                'license_plate': truck.license_plate,
                'model': truck.specific_model_name,
                'vin': truck.last_seven_vin,
                'client_id': truck.client.id if truck.client else None,
                'client_name': truck.client.name if truck.client else "Без власника"
            })
        return Response({'results': results})

    @action(detail=False, methods=['post'], url_path='check-maintenance')
    def check_maintenance(self, request):
        """Перевірка необхідності ТО."""
        return Response({'alerts': []})

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Статистика для дашборду."""
        queryset = ServiceOrder.objects.all()
        stats = {
            'total_orders': queryset.count(),
            'open_orders': queryset.filter(status='OPEN').count(),
            'in_progress_orders': queryset.filter(status='IN_PROGRESS').count(),
            'closed_orders': queryset.filter(status='CLOSED').count(),
            'canceled_orders': queryset.filter(status='CANCELED').count(),
        }
        return Response(stats)

    @action(detail=True, methods=['post'])
    def mark_for_deletion(self, request, pk=None):
        """Позначити замовлення на видалення."""
        order = self.get_object()
        order.marked_for_deletion = True
        order.marked_for_deletion_by = request.user
        order.marked_for_deletion_at = timezone.now()
        order.deletion_reason = request.data.get('reason', '')
        order.save()
        return Response({'status': 'success'})
    
    @action(detail=True, methods=['post'])
    def unmark_for_deletion(self, request, pk=None):
        """Зняти позначку на видалення."""
        order = self.get_object()
        order.marked_for_deletion = False
        order.deletion_reason = ''
        order.marked_for_deletion_by = None
        order.marked_for_deletion_at = None
        order.save()
        return Response({'status': 'success'})
    
    @action(detail=True, methods=['post'])
    def add_work(self, request, pk=None):
        """Додати роботу до замовлення."""
        order = self.get_object()
        serializer = ServiceWorkWriteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(service_order=order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServiceWorkViewSet(viewsets.ModelViewSet):
    """ViewSet для роботи з виконаними роботами."""
    queryset = ServiceWork.objects.select_related(
        'service_order', 'work', 'mechanic'
    ).all()
    serializer_class = ServiceWorkSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceWorkWriteSerializer
        return ServiceWorkSerializer

    @action(detail=True, methods=['post'], url_path='add-part')
    def add_part(self, request, pk=None):
        """Додати запчастину до роботи."""
        service_work = self.get_object()
        part_id = request.data.get('part')
        quantity = request.data.get('quantity', 1)
        unit_price = request.data.get('unit_price')
        
        try:
            used_part = UsedPart.objects.create(
                service_work=service_work,
                part_id=part_id,
                quantity=quantity,
                unit_price=unit_price
            )
            return Response(UsedPartSerializer(used_part).data, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=400)
            
    @action(detail=True, methods=['delete'], url_path='remove-part/(?P<part_id>[^/.]+)')
    def remove_part(self, request, pk=None, part_id=None):
        """Видалити запчастину з роботи."""
        try:
            UsedPart.objects.get(id=part_id, service_work_id=pk).delete()
            return Response(status=204)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class WorkGroupViewSet(viewsets.ModelViewSet):
    """ViewSet для груп робіт."""
    queryset = WorkGroup.objects.all()
    serializer_class = WorkGroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class WorkPriceViewSet(viewsets.ModelViewSet):
    """ViewSet для цін на роботи."""
    queryset = WorkPrice.objects.select_related('work_group').all()
    serializer_class = WorkPriceSerializer
    permission_classes = [permissions.IsAuthenticated]


class RepairPhotoViewSet(viewsets.ModelViewSet):
    """ViewSet для фото ремонту."""
    queryset = RepairPhoto.objects.select_related('service_order').all()
    serializer_class = RepairPhotoSerializer
    permission_classes = [permissions.IsAuthenticated]


class MaintenanceRuleViewSet(viewsets.ModelViewSet):
    """ViewSet для правил ТО."""
    queryset = MaintenanceRule.objects.all()
    serializer_class = MaintenanceRuleSerializer
    permission_classes = [permissions.IsAuthenticated]


class MaintenanceLogViewSet(viewsets.ModelViewSet):
    """ViewSet для журналу ТО."""
    queryset = MaintenanceLog.objects.select_related('truck', 'rule').all()
    serializer_class = MaintenanceLogSerializer
    permission_classes = [permissions.IsAuthenticated]


class MaintenanceKitViewSet(viewsets.ModelViewSet):
    """ViewSet для комплектів ТО."""
    queryset = MaintenanceKit.objects.select_related('truck', 'oil').all()
    serializer_class = MaintenanceKitSerializer
    permission_classes = [permissions.IsAuthenticated]