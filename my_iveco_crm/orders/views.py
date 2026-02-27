import logging
import datetime

from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend

logger = logging.getLogger(__name__)

from .models import (
    ServiceOrder, ServiceWork, WorkGroup, WorkPrice,
    RepairPhoto, MaintenanceRule, MaintenanceLog, MaintenanceKit, MaintenanceKitFilter,
    TruckMaintenanceIntervals,
    OrderStatusHistory,
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
    MaintenanceKitWriteSerializer,
    MaintenanceKitFilterSerializer,
    UsedPartSerializer,
    TruckMaintenanceIntervalsSerializer,
    OrderStatusHistorySerializer,
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
                'works__used_parts', 'works__used_parts__part', 'photos',
                'direct_parts', 'direct_parts__part',
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

    def perform_create(self, serializer):
        """При створенні фіксуємо автора початкового статусу."""
        instance = serializer.save()
        OrderStatusHistory.objects.filter(
            order=instance, from_status=''
        ).update(changed_by=self.request.user)

    def perform_update(self, serializer):
        """Передаємо поточного користувача в сигнал для запису автора зміни статусу."""
        serializer.instance._changed_by = self.request.user
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Фізичне видалення заборонено. Використовуйте позначення на видалення."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(detail=True, methods=['get'], url_path='status-history')
    def status_history(self, request, pk=None):
        """Хронологія змін статусу замовлення."""
        order = self.get_object()
        history = order.status_history.select_related('changed_by').order_by('changed_at')
        serializer = OrderStatusHistorySerializer(history, many=True)
        return Response(serializer.data)

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

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Підсумок кількості замовлень за день, тиждень, місяць та рік."""
        today = timezone.now().date()
        start_of_week = today - datetime.timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)

        qs = ServiceOrder.objects.filter(marked_for_deletion=False)
        return Response({
            'today': qs.filter(created_at__date=today).count(),
            'week': qs.filter(created_at__date__gte=start_of_week).count(),
            'month': qs.filter(created_at__date__gte=start_of_month).count(),
            'year': qs.filter(created_at__date__gte=start_of_year).count(),
        })

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

    @action(detail=True, methods=['post'], url_path='apply_maintenance_set')
    def apply_maintenance_set(self, request, pk=None):
        """Застосувати набір ТО до наряду."""
        order = self.get_object()
        rule_id = request.data.get('rule_id')

        if not rule_id:
            return Response({'detail': 'rule_id є обовʼязковим'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rule = MaintenanceRule.objects.get(id=rule_id)
        except MaintenanceRule.DoesNotExist:
            return Response({'detail': 'Правило ТО не знайдено'}, status=status.HTTP_404_NOT_FOUND)

        try:
            kit = MaintenanceKit.objects.prefetch_related('filters').get(truck=order.truck)
        except MaintenanceKit.DoesNotExist:
            return Response(
                {'detail': 'Для цього авто не налаштовано комплект ТО. Додайте комплект у картці авто.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Очищаємо старі direct_parts цього наряду від запчастин набору ТО
        kit_part_ids = [kit.oil_id] + list(kit.filters.values_list('part_id', flat=True))
        UsedPart.objects.filter(
            service_order=order,
            service_work__isnull=True,
            part_id__in=kit_part_ids,
        ).delete()

        # Видаляємо попередньо застосований набір (якщо є), щоб уникнути дублювання
        ServiceWork.objects.filter(service_order=order, description=rule.name).delete()

        # Створюємо роботу для ТО
        service_work = ServiceWork.objects.create(
            service_order=order,
            description=rule.name,
            hours_spent=0,
            price_at_moment=0,
        )

        # Додаємо запчастини до роботи (не напряму до наряду)
        UsedPart.objects.create(
            service_work=service_work,
            part=kit.oil,
            quantity=kit.oil_quantity,
        )

        for kit_filter in kit.filters.all():
            UsedPart.objects.create(
                service_work=service_work,
                part=kit_filter.part,
                quantity=kit_filter.quantity,
            )

        # Логуємо виконання ТО
        MaintenanceLog.objects.create(
            truck=order.truck,
            rule=rule,
            date_performed=timezone.now().date(),
            mileage=order.current_mileage,
        )

        # Оновлюємо загальну вартість наряду
        order.update_total_cost()

        return Response(
            {'detail': f'Набір ТО "{rule.name}" застосовано до наряду'},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'], url_path='maintenance-countdown')
    def maintenance_countdown(self, request, pk=None):
        """Повертає відлік регламентних робіт для замовлення."""
        order = self.get_object()
        current_km = order.current_mileage

        try:
            intervals = order.truck.maintenance_intervals
        except TruckMaintenanceIntervals.DoesNotExist:
            intervals = None

        TYPES = [
            ('engine_oil',    'До заміни оливи в двигуні'),
            ('gearbox_oil',   'До заміни оливи в КПП/АКПП'),
            ('rear_axle_oil', 'До заміни оливи в задньому мості'),
            ('belts',         'До заміни ремнів/роликів'),
            ('chains',        'До заміни ланцюгів'),
        ]

        result = []
        for key, label in TYPES:
            interval = getattr(intervals, f'{key}_interval', None) if intervals else None
            last_km  = getattr(intervals, f'{key}_last_km', None) if intervals else None

            if interval is not None and last_km is not None and current_km is not None:
                remaining = last_km + interval - current_km
            else:
                remaining = None

            result.append({
                'key': key,
                'label': label,
                'interval': interval,
                'last_km': last_km,
                'remaining': remaining,
            })

        return Response({
            'current_km': current_km,
            'items': result,
        })


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

    @action(detail=True, methods=['post'], url_path='apply-kit')
    def apply_kit(self, request, pk=None):
        """
        Вручну додати набір ТО (оливу + фільтри) до роботи.
        Використовується кнопкою 'Додати набір ТО' на фронтенді.
        """
        work = self.get_object()
        truck = work.service_order.truck

        if not truck:
            return Response({'error': 'Вантажівка не вказана в замовленні'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            kit = MaintenanceKit.objects.prefetch_related('filters__part').get(truck=truck)
        except MaintenanceKit.DoesNotExist:
            return Response(
                {'error': f'Набір ТО для {truck.license_plate} не знайдено. Спочатку збережіть набір.'},
                status=status.HTTP_404_NOT_FOUND
            )

        added = []

        if kit.oil:
            UsedPart.objects.get_or_create(
                service_work=work,
                part=kit.oil,
                defaults={'quantity': kit.oil_quantity}
            )
            added.append({'name': kit.oil.name, 'quantity': str(kit.oil_quantity), 'type': 'oil'})

        for kit_filter in kit.filters.all():
            UsedPart.objects.get_or_create(
                service_work=work,
                part=kit_filter.part,
                defaults={'quantity': kit_filter.quantity}
            )
            added.append({'name': kit_filter.part.name, 'quantity': kit_filter.quantity, 'type': 'filter'})

        work.service_order.update_total_cost()

        return Response({'added': added, 'count': len(added)}, status=status.HTTP_200_OK)


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
    queryset = MaintenanceLog.objects.select_related('truck', 'rule').order_by('-date_performed')
    serializer_class = MaintenanceLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['truck']


class MaintenanceKitViewSet(viewsets.ModelViewSet):
    """ViewSet для комплектів ТО."""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['truck']

    def get_queryset(self):
        return MaintenanceKit.objects.select_related(
            'truck', 'oil'
        ).prefetch_related(
            'filters', 'filters__part'
        ).all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MaintenanceKitWriteSerializer
        return MaintenanceKitSerializer

    @action(detail=True, methods=['post'], url_path='add-filter')
    def add_filter(self, request, pk=None):
        """Додати фільтр до комплекту ТО."""
        kit = self.get_object()
        serializer = MaintenanceKitFilterSerializer(data={**request.data, 'maintenance_kit': kit.pk})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='remove-filter/(?P<filter_id>[^/.]+)')
    def remove_filter(self, request, pk=None, filter_id=None):
        """Видалити фільтр з комплекту ТО."""
        try:
            MaintenanceKitFilter.objects.get(id=filter_id, maintenance_kit_id=pk).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except MaintenanceKitFilter.DoesNotExist:
            return Response({'error': 'Фільтр не знайдено'}, status=status.HTTP_404_NOT_FOUND)


class MaintenanceKitFilterViewSet(viewsets.ModelViewSet):
    """ViewSet для окремих фільтрів комплекту ТО."""
    serializer_class = MaintenanceKitFilterSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['maintenance_kit']

    def get_queryset(self):
        return MaintenanceKitFilter.objects.select_related(
            'maintenance_kit', 'part'
        ).all()


class TruckMaintenanceIntervalsViewSet(viewsets.ModelViewSet):
    """ViewSet для інтервалів ТО."""
    serializer_class = TruckMaintenanceIntervalsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['truck']

    def get_queryset(self):
        return TruckMaintenanceIntervals.objects.select_related('truck').all()

