from django.shortcuts import render
from rest_framework import viewsets
from .models import ServiceOrder, ServiceWork
from inventory.models import UsedPart   
# Додаємо нові серіалізатори
from .serializers import (
    ServiceOrderListSerializer, 
    ServiceOrderDetailSerializer,
    ServiceWorkSerializer,
    UsedPartSerializer
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

class UsedPartViewSet(viewsets.ModelViewSet):
    queryset = UsedPart.objects.all()
    serializer_class = UsedPartSerializer