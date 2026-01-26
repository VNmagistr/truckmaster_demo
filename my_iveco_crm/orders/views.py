from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q
from .models import (
    ServiceOrder, ServiceWork, WorkGroup, WorkPrice, 
    RepairPhoto, MaintenanceRule, MaintenanceLog
)
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
    MaintenanceLogSerializer
)
from django_filters.rest_framework import DjangoFilterBackend

class IsAuthenticated(permissions.IsAuthenticated):
    pass

class ServiceOrderViewSet(viewsets.ModelViewSet):
    # ОПТИМІЗАЦІЯ: Завантажуємо все одразу, щоб не гальмувало (N+1 problem)
    queryset = ServiceOrder.objects.select_related(
        'client', 
        'truck', 
        'truck__client',          # <--- Ключове для швидкості відображення власника
        'marked_for_deletion_by'
    ).all().order_by('-created_at')
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    search_fields = [
        'order_number',
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
        
        # Для детального перегляду підвантажуємо пов'язані роботи та фото
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                'works',
                'works__work',
                'works__mechanic',
                'works__used_parts',
                'works__used_parts__part',
                'photos'
            )
            
        global_search = self.request.query_params.get('global_search', None)
        
        if global_search:
            queryset = queryset.filter(
                Q(order_number__icontains=global_search) |
                Q(truck__license_plate__icontains=global_search) |
                Q(client__name__icontains=global_search)
            )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Отримати останні замовлення для Dashboard"""
        recent_orders = self.get_queryset()[:10]
        serializer = ServiceOrderListSerializer(recent_orders, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Отримати статистику для Dashboard"""
        # Використовуємо чистий queryset для швидкості підрахунку
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
        order = self.get_object()
        reason = request.data.get('reason', '')
        
        order.marked_for_deletion = True
        order.marked_for_deletion_by = request.user
        order.marked_for_deletion_at = timezone.now()
        order.deletion_reason = reason
        order.save()
        
        return Response({'status': 'success', 'message': 'Наряд-замовлення позначено на видалення'})
    
    @action(detail=True, methods=['post'])
    def unmark_for_deletion(self, request, pk=None):
        order = self.get_object()
        
        order.marked_for_deletion = False
        order.marked_for_deletion_by = None
        order.marked_for_deletion_at = None
        order.deletion_reason = ''
        order.save()
        
        return Response({'status': 'success', 'message': 'Позначку на видалення знято'})

class ServiceWorkViewSet(viewsets.ModelViewSet):
    queryset = ServiceWork.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceWorkWriteSerializer
        return ServiceWorkSerializer

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

class MaintenanceLogViewSet(viewsets.ModelViewSet):from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q, Max
from .models import (
    ServiceOrder, ServiceWork, WorkGroup, WorkPrice, 
    RepairPhoto, MaintenanceRule, MaintenanceLog
)
from clients.models import Truck, Client
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
    MaintenanceLogSerializer
)
from django_filters.rest_framework import DjangoFilterBackend

class IsAuthenticated(permissions.IsAuthenticated):
    pass

class ServiceOrderViewSet(viewsets.ModelViewSet):
    # Оптимізований запит (вирішує проблему повільного завантаження)
    queryset = ServiceOrder.objects.select_related(
        'client', 
        'truck', 
        'truck__client',
        'marked_for_deletion_by'
    ).all().order_by('-created_at')
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    search_fields = [
        'order_number',
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
        
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                'works', 'works__work', 'works__mechanic', 
                'works__used_parts', 'works__used_parts__part', 'photos'
            )
            
        global_search = self.request.query_params.get('global_search', None)
        if global_search:
            queryset = queryset.filter(
                Q(order_number__icontains=global_search) |
                Q(truck__license_plate__icontains=global_search) |
                Q(client__name__icontains=global_search)
            )
        return queryset

    # --- НОВИЙ МЕТОД 1: Живий пошук авто ---
    @action(detail=False, methods=['get'])
    def search_truck(self, request):
        """
        API для пошуку авто по частині номера.
        Виклик: GET /api/orders/search-truck/?plate=1234
        """
        plate_query = request.query_params.get('plate', '').strip()
        
        if len(plate_query) < 2:
            return Response({'results': []}, status=status.HTTP_200_OK)

        # Шукаємо авто, назва яких містить введені символи
        trucks = Truck.objects.filter(
            license_plate__icontains=plate_query
        ).select_related('client')[:10]  # Обмежуємо до 10 результатів

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

    # --- НОВИЙ МЕТОД 2: Перевірка регламентів ---
    @action(detail=False, methods=['post'])
    def check_maintenance(self, request):
        """
        API для перевірки регламентів.
        Виклик: POST /api/orders/check-maintenance/
        Body: { "truck_id": 1, "current_mileage": 500000 }
        """
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
        # Знаходимо правила для моделі цього авто (або загальні)
        # Припускаємо, що rules прив'язані до base_model або загальні
        # Тут спрощено: беремо всі активні правила
        rules = MaintenanceRule.objects.all() 

        for rule in rules:
            # Шукаємо останній запис про виконання цього правила для цього авто
            last_log = MaintenanceLog.objects.filter(
                truck=truck, 
                rule=rule
            ).aggregate(last_mileage=Max('mileage'))
            
            last_mileage = last_log['last_mileage'] or 0
            next_due = last_mileage + rule.interval_mileage

            if current_mileage >= next_due:
                overdue = current_mileage - next_due
                alerts.append({
                    'rule_name': rule.name,
                    'last_service_mileage': last_mileage,
                    'next_due_mileage': next_due,
                    'overdue_by': overdue,
                    'message': f"⚠️ {rule.name}: Прострочено на {overdue} км!"
                })
            elif (next_due - current_mileage) < 1000:
                # Попередження, якщо залишилось менше 1000 км
                remaining = next_due - current_mileage
                alerts.append({
                    'rule_name': rule.name,
                    'message': f"ℹ️ {rule.name}: Скоро заміна (через {remaining} км)"
                })

        return Response({'alerts': alerts})

    # ... методи dashboard_stats, previous_maintenance, mark_for_deletion залишаються без змін ...
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        recent_orders = self.get_queryset()[:10]
        serializer = ServiceOrderListSerializer(recent_orders, many=True)
        return Response(serializer.data)

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
        if not order.truck: return Response({'results': []})
        previous_orders = ServiceOrder.objects.filter(truck=order.truck, status='CLOSED').exclude(id=order.id).order_by('-created_at')[:5]
        result = []
        for prev_order in previous_orders:
            works = prev_order.works.filter(Q(work__name__icontains='ТО') | Q(work__name__icontains='олив')).select_related('work')
            if works.exists():
                work_data = {'order_number': prev_order.order_number, 'date': prev_order.created_at, 'works': []}
                for work in works:
                    work_data['works'].append({'work_name': work.work.name if work.work else 'Інше'})
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
        order.save()
        return Response({'status': 'success'})

class ServiceWorkViewSet(viewsets.ModelViewSet):
    queryset = ServiceWork.objects.all()
    permission_classes = [IsAuthenticated]
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']: return ServiceWorkWriteSerializer
        return ServiceWorkSerializer

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
    queryset = MaintenanceLog.objects.all()
    serializer_class = MaintenanceLogSerializer
    permission_classes = [IsAuthenticated]