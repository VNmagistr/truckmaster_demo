from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import Client, Truck, IvecoBaseModel
from .serializers import ClientSerializer, TruckListSerializer, TruckDetailSerializer, IvecoBaseModelSerializer
from django_filters.rest_framework import DjangoFilterBackend

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    
    @action(detail=True, methods=['post'])
    def mark_for_deletion(self, request, pk=None):
        """Позначити клієнта на видалення"""
        client = self.get_object()
        reason = request.data.get('reason', '')
        
        client.marked_for_deletion = True
        client.marked_for_deletion_by = request.user
        client.marked_for_deletion_at = timezone.now()
        client.deletion_reason = reason
        client.save()
        
        return Response({
            'status': 'success',
            'message': 'Клієнта позначено на видалення'
        })
    
    @action(detail=True, methods=['post'])
    def unmark_for_deletion(self, request, pk=None):
        """Зняти позначку на видалення"""
        client = self.get_object()
        
        client.marked_for_deletion = False
        client.marked_for_deletion_by = None
        client.marked_for_deletion_at = None
        client.deletion_reason = ''
        client.save()
        
        return Response({
            'status': 'success',
            'message': 'Позначку на видалення знято'
        })

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
        queryset = Truck.objects.all()
        search = self.request.query_params.get('search', None)
        
        if search:
            queryset = queryset.filter(license_plate__icontains=search)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def mark_for_deletion(self, request, pk=None):
        """Позначити вантажівку на видалення"""
        truck = self.get_object()
        reason = request.data.get('reason', '')
        
        truck.marked_for_deletion = True
        truck.marked_for_deletion_by = request.user
        truck.marked_for_deletion_at = timezone.now()
        truck.deletion_reason = reason
        truck.save()
        
        return Response({
            'status': 'success',
            'message': 'Вантажівку позначено на видалення'
        })
    
    @action(detail=True, methods=['post'])
    def unmark_for_deletion(self, request, pk=None):
        """Зняти позначку на видалення"""
        truck = self.get_object()
        
        truck.marked_for_deletion = False
        truck.marked_for_deletion_by = None
        truck.marked_for_deletion_at = None
        truck.deletion_reason = ''
        truck.save()
        
        return Response({
            'status': 'success',
            'message': 'Позначку на видалення знято'
        })
