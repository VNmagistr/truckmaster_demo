from rest_framework import viewsets
from .models import Client, Truck, IvecoBaseModel
from .serializers import ClientSerializer, TruckListSerializer, TruckDetailSerializer, IvecoBaseModelSerializer
from django_filters.rest_framework import DjangoFilterBackend

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    
    def get_queryset(self):
        """
        Фільтруємо soft-deleted клієнтів за замовчуванням.
        Якщо явно передано show_deleted=true, показуємо всіх.
        """
        queryset = Client.objects.select_related().order_by('name')
        
        # Перевіряємо чи потрібно показати видалених
        show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'
        
        if not show_deleted:
            queryset = queryset.filter(marked_for_deletion=False)
        
        return queryset

# Створюємо ViewSet для довідника моделей, він нам знадобиться у формі
class IvecoBaseModelViewSet(viewsets.ModelViewSet):
    queryset = IvecoBaseModel.objects.all()
    serializer_class = IvecoBaseModelSerializer

class TruckViewSet(viewsets.ModelViewSet):
    queryset = Truck.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['client']

    # Ця функція дозволяє нам вибирати серіалізатор в залежності від дії
    def get_serializer_class(self):
        if self.action == 'list':
            return TruckListSerializer # Для списку
        return TruckDetailSerializer # Для всього іншого (створення, редагування)
    
    def get_queryset(self):
        """
        Фільтруємо soft-deleted вантажівки за замовчуванням.
        Оптимізуємо запити через select_related.
        """
        queryset = Truck.objects.select_related('client', 'base_model').order_by('license_plate')
        
        # Перевіряємо чи потрібно показати видалених
        show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'
        
        if not show_deleted:
            queryset = queryset.filter(marked_for_deletion=False)
        
        return queryset
    