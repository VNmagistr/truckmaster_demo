from rest_framework import viewsets
from .models import Client, Truck, IvecoBaseModel
from .serializers import ClientSerializer, TruckListSerializer, TruckDetailSerializer, IvecoBaseModelSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class IvecoBaseModelViewSet(viewsets.ModelViewSet):
    queryset = IvecoBaseModel.objects.all()
    serializer_class = IvecoBaseModelSerializer

class TruckViewSet(viewsets.ModelViewSet):
    queryset = Truck.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['client']
    search_fields = ['license_plate', 'last_seven_vin']

    def get_serializer_class(self):
        if self.action == 'list':
            return TruckListSerializer
        return TruckDetailSerializer
    
    def get_queryset(self):
        """
        Фільтрація вантажівок з точним співпадінням по номеру
        """
        queryset = super().get_queryset()
        
        # Точний пошук по номеру (license_plate)
        license_plate = self.request.query_params.get('license_plate', None)
        if license_plate:
            # Точне співпадіння, без урахування регістру
            queryset = queryset.filter(license_plate__iexact=license_plate)
        
        return queryset

