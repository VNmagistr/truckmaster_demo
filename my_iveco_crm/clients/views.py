from rest_framework import viewsets, filters
from .models import Client, Truck, IvecoBaseModel
from .serializers import ClientSerializer, TruckListSerializer, TruckDetailSerializer, IvecoBaseModelSerializer
from django_filters.rest_framework import DjangoFilterBackend

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    
    # 🔥 ДОДАНО: Підключаємо пошук
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    # Вказуємо поля, по яких шукати (можна частковий збіг)
    search_fields = ['name', 'phone', 'email', 'address'] 
    
    def get_queryset(self):
        """
        ТИМЧАСОВО БЕЗ ФІЛЬТРА для дебагу
        """
        queryset = Client.objects.all().order_by('name')
        
        # ЗАКОМЕНТОВАНО фільтр
        # show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'
        # if not show_deleted:
        #     queryset = queryset.filter(marked_for_deletion=False)
        
        return queryset

# Створюємо ViewSet для довідника моделей, він нам знадобиться у формі
class IvecoBaseModelViewSet(viewsets.ModelViewSet):
    queryset = IvecoBaseModel.objects.all()
    serializer_class = IvecoBaseModelSerializer

class TruckViewSet(viewsets.ModelViewSet):
    queryset = Truck.objects.all()
    
    # 🔥 ОНОВЛЕНО: Додано SearchFilter до списку фільтрів
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['client']
    # Вказуємо поля для пошуку вантажівок
    search_fields = ['license_plate', 'full_vin', 'last_seven_vin', 'specific_model_name']

    # Ця функція дозволяє нам вибирати серіалізатор в залежності від дії
    def get_serializer_class(self):
        if self.action == 'list':
            return TruckListSerializer # Для списку
        return TruckDetailSerializer # Для всього іншого (створення, редагування)
    
    def get_queryset(self):
        """
        ТИМЧАСОВО БЕЗ ФІЛЬТРА для дебагу
        """
        queryset = Truck.objects.select_related('client', 'base_model').order_by('license_plate')
        
        # ЗАКОМЕНТОВАНО фільтр
        # show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'
        # if not show_deleted:
        #     queryset = queryset.filter(marked_for_deletion=False)
        
        return queryset