# orders/views.py

from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.views import APIView # <-- Додайте імпорт
from rest_framework.response import Response # <-- Додайте імпорт
from django.db.models import Count # <-- Додайте імпорт
from rest_framework.parsers import MultiPartParser, FormParser
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

# --- НОВИЙ VIEW ДЛЯ СТАТИСТИКИ ---
class OrderStatsByStatusView(APIView):
    """
    Повертає кількість замовлень, згрупованих за статусом.
    """
    def get(self, request, format=None):
        # Агрегуємо дані: групуємо за полем 'status' і рахуємо кількість в кожній групі
        stats = ServiceOrder.objects.values('status').annotate(count=Count('status'))
        
        # Перетворюємо статуси з 'new' на 'Нове' для зручності на фронтенді
        status_map = dict(ServiceOrder.StatusChoices.choices)
        data_for_chart = [
            {'status': status_map.get(item['status'], item['status']), 'count': item['count']}
            for item in stats
        ]
        return Response(data_for_chart)


class ServiceOrderViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrder.objects.select_related('client', 'truck').all()
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']
    parser_classes = (MultiPartParser, FormParser)

    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceOrderListSerializer
        
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceOrderWriteSerializer
        
        return ServiceOrderDetailSerializer

class RecentOrdersViewSet(viewsets.ReadOnlyModelViewSet):
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