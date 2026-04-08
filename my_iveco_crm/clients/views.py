from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from .models import Client, Truck, IvecoBaseModel
from .serializers import ClientSerializer, TruckListSerializer, TruckDetailSerializer, IvecoBaseModelSerializer
from django_filters.rest_framework import DjangoFilterBackend
from users.permissions import IsAdminRole, IsManagerOrAbove


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'phone', 'email', 'address']

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAuthenticated(), IsAdminRole()]
        if self.action in ('create', 'update', 'partial_update'):
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Client.objects.all().order_by('name')
        show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'
        if not show_deleted:
            queryset = queryset.filter(marked_for_deletion=False)
        return queryset


class IvecoBaseModelViewSet(viewsets.ModelViewSet):
    queryset = IvecoBaseModel.objects.all()
    serializer_class = IvecoBaseModelSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated()]


class TruckViewSet(viewsets.ModelViewSet):
    queryset = Truck.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['client', 'euro_standard', 'base_model']
    search_fields = ['license_plate', 'full_vin', 'last_seven_vin', 'specific_model_name']
    ordering_fields = ['license_plate', 'specific_model_name', 'euro_standard']

    def get_serializer_class(self):
        if self.action == 'list':
            return TruckListSerializer
        return TruckDetailSerializer

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAuthenticated(), IsAdminRole()]
        if self.action in ('create', 'update', 'partial_update'):
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Truck.objects.select_related('client', 'base_model').order_by('license_plate')
        show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'
        if not show_deleted:
            queryset = queryset.filter(marked_for_deletion=False)
        return queryset