from rest_framework import viewsets, permissions, status
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
from inventory.models import UsedPart

# Визначаємо права доступу
class IsAuthenticated(permissions.IsAuthenticated):
    pass

# --- ViewSet для Замовлень-Нарядів ---
class ServiceOrderViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrder.objects.all().order_by('-created_at')
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceOrderListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceOrderWriteSerializer
        return ServiceOrderDetailSerializer

    @action(detail=False, methods=['get'], url_path='previous-parts')
    def previous_parts(self, request):
        """
        Отримати запчастини з попередніх замовлень для конкретної вантажівки та типу робіт.
        
        Query параметри:
        - truck_id: ID вантажівки (обов'язковий)
        - work_group_id: ID категорії робіт (опціонально, для фільтрації)
        - work_id: ID конкретної роботи (опціонально, для більш точного пошуку)
        """
        truck_id = request.query_params.get('truck_id')
        work_group_id = request.query_params.get('work_group_id')
        work_id = request.query_params.get('work_id')
        
        if not truck_id:
            return Response(
                {'error': 'truck_id є обов\'язковим параметром'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Шукаємо попередні замовлення для цієї вантажівки
        previous_orders = ServiceOrder.objects.filter(
            truck_id=truck_id,
            status__in=['CLOSED', 'IN_PROGRESS']  # Тільки закриті або в роботі
        ).order_by('-created_at')
        
        if not previous_orders.exists():
            return Response({
                'message': 'Попередніх замовлень не знайдено',
                'parts': []
            })
        
        # Фільтруємо роботи за типом, якщо вказано
        works_filter = Q()
        if work_id:
            works_filter = Q(work_id=work_id)
        elif work_group_id:
            works_filter = Q(work__work_group_id=work_group_id)
        
        # Збираємо запчастини з попередніх робіт
        used_parts = UsedPart.objects.filter(
            service_work__service_order__in=previous_orders
        ).filter(works_filter).select_related(
            'part',
            'part__subcategory',
            'service_work',
            'service_work__work',
            'service_work__service_order'
        ).order_by('-service_work__service_order__created_at')
        
        # Групуємо запчастини та беремо найостанніше використання кожної
        parts_dict = {}
        for used_part in used_parts:
            part_id = used_part.part.id
            if part_id not in parts_dict:
                parts_dict[part_id] = {
                    'part_id': part_id,
                    'part_name': used_part.part.name,
                    'part_sku': used_part.part.sku_code,
                    'part_brand': used_part.part.brand,
                    'subcategory': used_part.part.subcategory.name if used_part.part.subcategory else None,
                    'quantity': used_part.quantity,
                    'current_price': float(used_part.part.selling_price),
                    'current_stock': used_part.part.current_stock,
                    'last_used_date': used_part.service_work.service_order.created_at.isoformat(),
                    'last_order_number': used_part.service_work.service_order.order_number,
                    'work_name': used_part.service_work.work.name if used_part.service_work.work else None,
                }
        
        parts_list = list(parts_dict.values())
        
        return Response({
            'truck_id': truck_id,
            'previous_orders_count': previous_orders.count(),
            'last_order': {
                'order_number': previous_orders.first().order_number,
                'date': previous_orders.first().created_at.isoformat(),
            } if previous_orders.exists() else None,
            'parts': parts_list,
            'total_parts': len(parts_list)
        })

# --- ViewSet для Виконаних Робіт ---
class ServiceWorkViewSet(viewsets.ModelViewSet):
    queryset = ServiceWork.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceWorkWriteSerializer
        return ServiceWorkSerializer

# --- Інші ViewSets ---
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
    