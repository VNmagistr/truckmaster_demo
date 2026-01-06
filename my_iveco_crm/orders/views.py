from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
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
from inventory.serializers import UsedPartSerializer

# Визначаємо права доступу (наприклад, тільки для адмінів або залогінених)
# Для простоти поки що - тільки для залогінених
class IsAuthenticated(permissions.IsAuthenticated):
    pass

# --- ViewSet для Замовлень-Нарядів ---
class ServiceOrderViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrder.objects.all().order_by('-created_at')
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        # Для списку - простий серіалізатор
        if self.action == 'list':
            return ServiceOrderListSerializer
        # Для створення/оновлення - серіалізатор для запису
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceOrderWriteSerializer
        # Для перегляду одного об'єкта - повний серіалізатор
        return ServiceOrderDetailSerializer

    @action(detail=True, methods=['get'])
    def previous_maintenance(self, request, pk=None):
        """
        Повертає запчастини з попереднього ТО для цієї вантажівки.
        Фільтрує по категорії робіт (олива, фільтри).
        """
        try:
            current_order = self.get_object()
            
            if not current_order.truck:
                return Response(
                    {'detail': 'Вантажівка не вказана в цьому замовленні'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Знаходимо попередні замовлення для цієї вантажівки
            previous_orders = ServiceOrder.objects.filter(
                truck=current_order.truck,
                status__in=['CLOSED', 'IN_PROGRESS']
            ).exclude(
                id=current_order.id
            ).order_by('-created_at')[:5]  # Останні 5 замовлень
            
            if not previous_orders.exists():
                return Response({
                    'has_previous': False,
                    'message': 'Для цієї вантажівки немає попередніх замовлень'
                })
            
            # Збираємо інформацію про попередні ТО
            maintenance_history = []
            
            for order in previous_orders:
                # Знаходимо всі роботи пов'язані з ТО
                maintenance_works = ServiceWork.objects.filter(
                    service_order=order,
                    work__work_group__name__icontains='ТО'  # Фільтруємо по категорії
                ) | ServiceWork.objects.filter(
                    service_order=order,
                    work__name__icontains='олив'  # Або по назві роботи
                ) | ServiceWork.objects.filter(
                    service_order=order,
                    work__name__icontains='фільтр'
                )
                
                maintenance_works = maintenance_works.distinct()
                
                if maintenance_works.exists():
                    # Збираємо запчастини з цих робіт
                    used_parts = UsedPart.objects.filter(
                        service_work__in=maintenance_works
                    ).select_related('part', 'part__subcategory')
                    
                    if used_parts.exists():
                        parts_data = []
                        for used_part in used_parts:
                            parts_data.append({
                                'id': used_part.part.id,
                                'name': used_part.part.name,
                                'sku_code': used_part.part.sku_code,
                                'quantity': used_part.quantity,
                                'subcategory': used_part.part.subcategory.name if used_part.part.subcategory else None,
                                'unit': used_part.part.unit,
                                'selling_price': float(used_part.part.selling_price),
                            })
                        
                        maintenance_history.append({
                            'order_id': order.id,
                            'order_number': order.order_number,
                            'created_at': order.created_at,
                            'current_mileage': order.current_mileage,
                            'parts': parts_data,
                            'works': [{
                                'name': work.work.name if work.work else work.description,
                                'description': work.description,
                            } for work in maintenance_works]
                        })
            
            if not maintenance_history:
                return Response({
                    'has_previous': False,
                    'message': 'Для цієї вантажівки немає попередніх робіт по ТО'
                })
            
            return Response({
                'has_previous': True,
                'truck': {
                    'id': current_order.truck.id,
                    'license_plate': current_order.truck.license_plate,
                    'specific_model_name': current_order.truck.specific_model_name,
                },
                'maintenance_history': maintenance_history
            })
            
        except Exception as e:
            return Response(
                {'detail': f'Помилка: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
