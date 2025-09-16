from django.shortcuts import render
from rest_framework import viewsets
from .models import ServiceOrder, ServiceWork, Employee, WorkGroup 
from inventory.models import UsedPart 
# Додаємо нові серіалізатори
from .serializers import (
    ServiceOrderListSerializer, 
    ServiceOrderDetailSerializer,
    ServiceWorkSerializer,
    UsedPartSerializer,
    EmployeeSerializer,
    WorkGroupSerializer
)

class ServiceOrderViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrder.objects.select_related('client', 'truck').all()

    def get_serializer_class(self):
        # Для детального перегляду (retrieve) використовуємо детальний серіалізатор
        if self.action in ['retrieve', 'update', 'partial_update', 'create']:
            return ServiceOrderDetailSerializer
        return ServiceOrderListSerializer

# Нові ViewSet'и
class ServiceWorkViewSet(viewsets.ModelViewSet):
    queryset = ServiceWork.objects.all()
    serializer_class = ServiceWorkSerializer

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

class UsedPartViewSet(viewsets.ModelViewSet):
    queryset = UsedPart.objects.all()
    serializer_class = UsedPartSerializer

class WorkGroupViewSet(viewsets.ModelViewSet):
    queryset = WorkGroup.objects.all()
    serializer_class = WorkGroupSerializer