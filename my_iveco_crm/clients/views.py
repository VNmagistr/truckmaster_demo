from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Client, Truck, IvecoBaseModel
from .serializers import ClientSerializer, TruckListSerializer, IvecoBaseModelSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer


class TruckViewSet(viewsets.ModelViewSet):
    queryset = Truck.objects.select_related('client', 'base_model').all()
    serializer_class = TruckListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['client']

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Пошук автомобілів за частиною номерного знаку"""
        query = request.query_params.get('license_plate', '')
        
        if len(query) < 2:
            return Response({'results': []})
        
        trucks = Truck.objects.filter(
            license_plate__icontains=query
        ).select_related('client')[:10]
        
        results = [{
            'id': truck.id,
            'license_plate': truck.license_plate,
            'vin_code': truck.vin_code,
            'last_seven_vin': truck.last_seven_vin,
            'specific_model_name': truck.specific_model_name,
            'client_id': truck.client_id,
            'client_name': truck.client.name if truck.client else 'Невідомий клієнт',
        } for truck in trucks]
        
        return Response({'results': results})


class IvecoBaseModelViewSet(viewsets.ModelViewSet):
    queryset = IvecoBaseModel.objects.all()
    serializer_class = IvecoBaseModelSerializer

