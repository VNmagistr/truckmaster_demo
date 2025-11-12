from rest_framework import viewsets, permissions
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