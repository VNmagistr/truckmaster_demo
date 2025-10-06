from django.shortcuts import render
from rest_framework import viewsets
from .models import ServiceOrder, ServiceWork, Employee, WorkGroup, RepairPhoto
from inventory.models import UsedPart 

# 1. Імпортуємо ВСІ необхідні серіалізатори
from .serializers import (
    RepairPhotoSerializer,
    ServiceOrderListSerializer, 
    ServiceOrderDetailSerializer,
    ServiceOrderWriteSerializer,  # <-- Додано імпорт
    ServiceWorkSerializer,
    UsedPartSerializer,
    EmployeeSerializer,
    WorkGroupSerializer
)

class ServiceOrderViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrder.objects.select_related('client', 'truck').all()

    # 2. Оновлюємо логіку вибору серіалізатора
    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceOrderListSerializer
        
        # Для створення та оновлення використовуємо наш новий серіалізатор для ЗАПИСУ
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceOrderWriteSerializer
        
        # Для всього іншого (детальний перегляд) використовуємо детальний серіалізатор
        return ServiceOrderDetailSerializer

# --- Інші ViewSet'и без змін ---

class ServiceWorkViewSet(viewsets.ModelViewSet):
    queryset = ServiceWork.objects.all()
    serializer_class = ServiceWorkSerializer

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

class UsedPartViewSet(viewsets.ModelViewSet):
    queryset = UsedPart.objects.all()
    serializer_class = UsedPartSerializer

# Рекомендація: Зробити цей ViewSet тільки для читання,
# щоб випадково не змінити прайс-лист через API
class WorkGroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WorkGroup.objects.all()
    serializer_class = WorkGroupSerializer

class RepairPhotoViewSet(viewsets.ModelViewSet):
    queryset = RepairPhoto.objects.all()
    serializer_class = RepairPhotoSerializer