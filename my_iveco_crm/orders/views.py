from django.shortcuts import render
from rest_framework import viewsets
from .models import ServiceOrder, ServiceWork, Employee, WorkCategory, Work, RepairPhoto
from inventory.models import UsedPart 

from .serializers import (
    RepairPhotoSerializer,
    ServiceOrderListSerializer, 
    ServiceOrderDetailSerializer,
    ServiceOrderWriteSerializer,
    ServiceWorkWriteSerializer,
    UsedPartSerializer,
    EmployeeSerializer,
    WorkCategorySerializer
)

class ServiceOrderViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrder.objects.select_related('client', 'truck').all()
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceOrderListSerializer
        
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceOrderWriteSerializer
        
        return ServiceOrderDetailSerializer

# --- НОВИЙ VIEWSET ДЛЯ ДАШБОРДУ ---
class RecentOrdersViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Повертає 5 останніх наряд-замовлень для відображення на дашборді.
    """
    queryset = ServiceOrder.objects.order_by('-start_date')[:5]
    serializer_class = ServiceOrderListSerializer


class WorkCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WorkCategory.objects.prefetch_related('works').all()
    serializer_class = WorkCategorySerializer

class ServiceWorkViewSet(viewsets.ModelViewSet):
    queryset = ServiceWork.objects.all()
    serializer_class = ServiceWorkWriteSerializer

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

class UsedPartViewSet(viewsets.ModelViewSet):
    queryset = UsedPart.objects.all()
    serializer_class = UsedPartSerializer

class RepairPhotoViewSet(viewsets.ModelViewSet):
    queryset = RepairPhoto.objects.all()
    serializer_class = RepairPhotoSerializer