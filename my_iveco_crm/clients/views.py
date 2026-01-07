from rest_framework import viewsets
from .models import Client, Truck, IvecoBaseModel
from .serializers import ClientSerializer, TruckListSerializer, TruckDetailSerializer, IvecoBaseModelSerializer
from django_filters.rest_framework import DjangoFilterBackend

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class IvecoBaseModelViewSet(viewsets.ModelViewSet):
    queryset = IvecoBaseModel.objects.all()
    serializer_class = IvecoBaseModelSerializer

class TruckViewSet(viewsets.ModelViewSet):
    queryset = Truck.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['client']

    def get_serializer_class(self):
        if self.action == 'list':
            return TruckListSerializer
        return TruckDetailSerializer
    
    def get_queryset(self):
        """
        Фільтрація вантажівок ТІЛЬКИ по держномеру (license_plate)
        """
        queryset = super().get_queryset()
        
        # Пошук по номеру з частковим співпадінням
        license_plate = self.request.query_params.get('license_plate', None)
        if license_plate:
            # Часткове співпадіння в номері, без урахування регістру
            queryset = queryset.filter(license_plate__icontains=license_plate)
        
        return queryset
    