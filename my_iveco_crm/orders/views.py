from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count
from datetime import datetime, timedelta
from django.utils import timezone
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

# --- View для останніх замовлень ---
class RecentOrdersView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Отримуємо 10 останніх замовлень
        recent_orders = ServiceOrder.objects.all().order_by('-created_at')[:10]
        serializer = ServiceOrderListSerializer(recent_orders, many=True)
        return Response(serializer.data)

# --- View для статистики dashboard ---
class DashboardOrderStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        now = timezone.now()
        
        # Поточний тиждень
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=7)
        this_week = ServiceOrder.objects.filter(
            created_at__gte=week_start,
            created_at__lt=week_end
        ).count()
        
        # Минулий тиждень (для порівняння)
        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = week_start
        compare_week = ServiceOrder.objects.filter(
            created_at__gte=prev_week_start,
            created_at__lt=prev_week_end
        ).count()
        
        # Поточний місяць
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month = ServiceOrder.objects.filter(
            created_at__gte=month_start
        ).count()
        
        # Минулий місяць
        if month_start.month == 1:
            prev_month_start = month_start.replace(year=month_start.year - 1, month=12)
        else:
            prev_month_start = month_start.replace(month=month_start.month - 1)
        compare_month = ServiceOrder.objects.filter(
            created_at__gte=prev_month_start,
            created_at__lt=month_start
        ).count()
        
        # Поточний рік
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        this_year = ServiceOrder.objects.filter(
            created_at__gte=year_start
        ).count()
        
        # Минулий рік
        prev_year_start = year_start.replace(year=year_start.year - 1)
        compare_year = ServiceOrder.objects.filter(
            created_at__gte=prev_year_start,
            created_at__lt=year_start
        ).count()
        
        return Response({
            'this_week': this_week,
            'compare_week': compare_week,
            'this_month': this_month,
            'compare_month': compare_month,
            'this_year': this_year,
            'compare_year': compare_year,
        })