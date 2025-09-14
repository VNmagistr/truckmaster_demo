from rest_framework import viewsets
from .models import Client, Truck, IvecoBaseModel # Додаємо IvecoBaseModel
# Імпортуємо всі нові серіалізатори
from .serializers import ClientSerializer, TruckListSerializer, TruckDetailSerializer, IvecoBaseModelSerializer

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

# Створюємо ViewSet для довідника моделей, він нам знадобиться у формі
class IvecoBaseModelViewSet(viewsets.ModelViewSet):
    queryset = IvecoBaseModel.objects.all()
    serializer_class = IvecoBaseModelSerializer

class TruckViewSet(viewsets.ModelViewSet):
    queryset = Truck.objects.all()

    # Ця функція дозволяє нам вибирати серіалізатор в залежності від дії
    def get_serializer_class(self):
        if self.action == 'list':
            return TruckListSerializer # Для списку
        return TruckDetailSerializer # Для всього іншого (створення, редагування)