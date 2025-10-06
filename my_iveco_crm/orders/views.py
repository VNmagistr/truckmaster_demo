# orders/views.py

from django.shortcuts import render
from rest_framework import viewsets
# 1. Оновлюємо імпорти моделей: WorkGroup -> WorkCategory, Work
from .models import ServiceOrder, ServiceWork, Employee, WorkCategory, Work, RepairPhoto
from inventory.models import UsedPart 

# 2. Оновлюємо імпорти серіалізаторів
from .serializers import (
    RepairPhotoSerializer,
    ServiceOrderListSerializer, 
    ServiceOrderDetailSerializer,
    ServiceOrderWriteSerializer,
    ServiceWorkSerializer,
    UsedPartSerializer,
    EmployeeSerializer,
    WorkCategorySerializer # <-- Замість WorkGroupSerializer
)

class ServiceOrderViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrder.objects.select_related('client', 'truck').all()

    # Ця логіка залишається правильною
    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceOrderListSerializer
        
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceOrderWriteSerializer
        
        return ServiceOrderDetailSerializer

# --- 3. Замінюємо WorkGroupViewSet на WorkCategoryViewSet ---
class WorkCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Віддає список категорій робіт, включаючи вкладений список самих робіт.
    """
    queryset = WorkCategory.objects.prefetch_related('works').all()
    serializer_class = WorkCategorySerializer


# --- Інші ViewSet'и залишаються без змін ---

class ServiceWorkViewSet(viewsets.ModelViewSet):
    queryset = ServiceWork.objects.all()
    serializer_class = ServiceWorkSerializer

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

class UsedPartViewSet(viewsets.ModelViewSet):
    queryset = UsedPart.objects.all()
    serializer_class = UsedPartSerializer

class RepairPhotoViewSet(viewsets.ModelViewSet):
    queryset = RepairPhoto.objects.all()
    serializer_class = RepairPhotoSerializer