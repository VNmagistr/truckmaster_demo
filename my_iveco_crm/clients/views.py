from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from .models import Client, IvecoBaseModel, Truck
from .serializers import ClientSerializer, IvecoBaseModelSerializer, TruckDetailSerializer, TruckListSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'phone', 'email', 'address']

    def get_queryset(self):
        queryset = Client.objects.all().order_by('name')

        show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'
        if not show_deleted:
            queryset = queryset.filter(marked_for_deletion=False)

        return queryset


class IvecoBaseModelViewSet(viewsets.ModelViewSet):
    queryset = IvecoBaseModel.objects.all()
    serializer_class = IvecoBaseModelSerializer


class TruckViewSet(viewsets.ModelViewSet):
    queryset = Truck.objects.all()

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['client']
    search_fields = ['license_plate', 'full_vin', 'last_seven_vin', 'specific_model_name']

    def get_serializer_class(self):
        if self.action == 'list':
            return TruckListSerializer
        return TruckDetailSerializer

    def get_queryset(self):
        queryset = Truck.objects.select_related('client', 'base_model').order_by('license_plate')

        show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'
        if not show_deleted:
            queryset = queryset.filter(marked_for_deletion=False)

        return queryset
