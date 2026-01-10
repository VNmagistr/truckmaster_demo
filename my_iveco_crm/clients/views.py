from rest_framework import viewsets
from .models import Client, Truck, IvecoBaseModel
from .serializers import ClientSerializer, TruckListSerializer, TruckDetailSerializer, IvecoBaseModelSerializer
from django_filters.rest_framework import DjangoFilterBackend

class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['marked_for_deletion']
    
    def get_queryset(self):
        """Фільтруємо видалені клієнти за замовчуванням"""
        queryset = Client.objects.all()
        
        # Якщо явно не запитано marked_for_deletion, показуємо тільки активні
        if 'marked_for_deletion' not in self.request.query_params:
            queryset = queryset.filter(marked_for_deletion=False)
        
        return queryset.select_related().order_by('name')


class IvecoBaseModelViewSet(viewsets.ModelViewSet):
    queryset = IvecoBaseModel.objects.all()
    serializer_class = IvecoBaseModelSerializer


class TruckViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['client', 'marked_for_deletion']

    def get_queryset(self):
        """Фільтруємо видалені вантажівки за замовчуванням"""
        queryset = Truck.objects.all()
        
        # Якщо явно не запитано marked_for_deletion, показуємо тільки активні
        if 'marked_for_deletion' not in self.request.query_params:
            queryset = queryset.filter(marked_for_deletion=False)
        
        return queryset.select_related('client', 'base_model').order_by('license_plate')

    def get_serializer_class(self):
        if self.action == 'list':
            return TruckListSerializer
        return TruckDetailSerializer
    