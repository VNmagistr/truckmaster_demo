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
    queryset = Truck.objects.select_related('client', 'base_model').all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['client']

    def get_serializer_class(self):
        if self.action == 'list':
            return TruckListSerializer
        return TruckDetailSerializer