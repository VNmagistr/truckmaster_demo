from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Max
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
    queryset = ServiceOrder.objects.select_related(
        'client', 
        'truck', 
        'truck__client',
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
        
        # Якщо ми переглядаємо деталі (retrieve) - показуємо все, навіть видалене
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                'works', 'works__work', 'works__mechanic', 
                'works__used_parts', 'works__used_parts__part', 'photos'
            )
            return queryset
            
        # Якщо це список (list), за замовчуванням ховаємо помічені на видалення,
        # АЛЕ якщо користувач хоче їх бачити (фільтр у URL), то показуємо.
        if self.action == 'list':
             # Якщо фронтенд прямо не просить ?marked_for_deletion=true/false,
             # то показуємо тільки живі замовлення.
             marked_param = self.request.query_params.get('marked_for_deletion')
             if marked_param is None:
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
        """Забороняємо фізичне видалення через API."""
        return Response(
            {"detail": "Фізичне видалення заборонено. Використовуйте позначення на видалення."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(detail=False, methods=['get'], url_path='search-truck')
    def search_truck(self, request):
        plate_query = request.query_params.get('plate', '').strip()
        if len(plate_query) < 2:
            return Response({'results': []}, status=status.HTTP_200_OK)

        trucks = Truck.objects.filter(
            license_plate__icontains=plate_query
        ).select_related('client')[:10]

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
        truck_id = request.data.get('truck_id')
        current_mileage = request.data.get('current_mileage')

        if not truck_id or not current_mileage:
            return Response({'error': 'No truck_id or mileage provided'}, status=400)

        try:
            current_mileage = int(current_mileage)
            truck = Truck.objects.get(id=truck_id)
        except (ValueError, Truck.DoesNotExist):
            return Response({'alerts': []})

        alerts = []
        rules = MaintenanceRule.objects.all() 

        for rule in rules:
            last_log = MaintenanceLog.objects.filter(
                truck=truck, 
                rule=rule
            ).order_by('-id').first() 
            
            last_mileage = getattr(last_log, 'mileage', 0) if last_log else 0
            
            if rule.km_interval:
                next_due = last_mileage + rule.km_interval
                if current_mileage >= next_due:
                    overdue = current_mileage - next_due
                    alerts.append({
                        'rule_name': rule.name,
                        'message': f"⚠️ {rule.name}: Прострочено на {overdue} км!"
                    })
                elif (next_due - current_mileage) < 1000:
                    remaining = next_due - current_mileage
                    alerts.append({
                        'rule_name': rule.name,
                        'message': f"ℹ️ {rule.name}: Скоро заміна (через {remaining} км)"
                    })

        return Response({'alerts': alerts})
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        queryset = ServiceOrder.objects.all()
        stats = {
            'total_orders': queryset.count(),
            'open_orders': queryset.filter(status='OPEN').count(),
            'in_progress_orders': queryset.filter(status='IN_PROGRESS').count(),
            'closed_orders': queryset.filter(status='CLOSED').count(),
            'canceled_orders': queryset.filter(status='CANCELED').count(),
        }
        return Response(stats)

    @action(detail=True, methods=['get'])
    def previous_maintenance(self, request, pk=None):
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
                Q(work__name__icontains='ТО') | Q(work__name__icontains='олив')
            ).select_related('work')
            
            if works.exists():
                work_data = {
                    'order_number': prev_order.order_number, 
                    'date': prev_order.created_at, 
                    'works': []
                }
                for work in works:
                    work_data['works'].append({
                        'work_name': work.work.name if work.work else 'Інше'
                    })
                result.append(work_data)
        
        return Response({'results': result})
    
    @action(detail=True, methods=['post'])
    def mark_for_deletion(self, request, pk=None):
        order = self.get_object()
        order.marked_for_deletion = True
        order.marked_for_deletion_by = request.user
        order.marked_for_deletion_at = timezone.now()
        order.deletion_reason = request.data.get('reason', '')
        order.save()
        return Response({'status': 'success'})
    
    @action(detail=True, methods=['post'])
    def unmark_for_deletion(self, request, pk=None):
        order = self.get_object()
        order.marked_for_deletion = False
        order.deletion_reason = ''
        order.marked_for_deletion_by = None
        order.marked_for_deletion_at = None
        order.save()
        return Response({'status': 'success'})


class ServiceWorkViewSet(viewsets.ModelViewSet):
    queryset = ServiceWork.objects.all()
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
        warehouse_id = request.data.get('warehouse')
        
        if not part_id:
            return Response(
                {'error': 'Необхідно вказати запчастину (part)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            used_part = UsedPart.objects.create(
                service_work=service_work,
                part_id=part_id,
                quantity=quantity,
                unit_price=unit_price,
                warehouse_id=warehouse_id
            )
            
            # Оновлюємо загальну вартість замовлення
            service_work.service_order.update_total_cost()
            
            serializer = UsedPartSerializer(used_part)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['delete'], url_path='remove-part/(?P<part_id>[^/.]+)')
    def remove_part(self, request, pk=None, part_id=None):
        """Видалити запчастину з роботи."""
        service_work = self.get_object()
        
        try:
            used_part = UsedPart.objects.get(id=part_id, service_work=service_work)
            used_part.delete()
            
            # Оновлюємо загальну вартість замовлення
            service_work.service_order.update_total_cost()
            
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
            
        except UsedPart.DoesNotExist:
            return Response(
                {'error': 'Запчастину не знайдено'},
                status=status.HTTP_404_NOT_FOUND
            )


class WorkGroupViewSet(viewsets.ModelViewSet):
    queryset = WorkGroup.objects.all()
    serializer_class = WorkGroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class WorkPriceViewSet(viewsets.ModelViewSet):
    queryset = WorkPrice.objects.all()
    serializer_class = WorkPriceSerializer
    permission_classes = [permissions.IsAuthenticated]


class RepairPhotoViewSet(viewsets.ModelViewSet):
    queryset = RepairPhoto.objects.all()
    serializer_class = RepairPhotoSerializer
    permission_classes = [permissions.IsAuthenticated]


class MaintenanceRuleViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRule.objects.all()
    serializer_class = MaintenanceRuleSerializer
    permission_classes = [permissions.IsAuthenticated]


class MaintenanceLogViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceLog.objects.all()
    serializer_class = MaintenanceLogSerializer
    permission_classes = [permissions.IsAuthenticated]


class MaintenanceKitViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceKit.objects.all()
    serializer_class = MaintenanceKitSerializer
    permission_classes = [permissions.IsAuthenticated]