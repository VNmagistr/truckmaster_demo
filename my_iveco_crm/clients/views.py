from django.shortcuts import render
from rest_framework import viewsets
from .models import Client, Truck
from .serializers import ClientSerializer, TruckSerializer

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class TruckViewSet(viewsets.ModelViewSet):
    queryset = Truck.objects.all()
    serializer_class = TruckSerializer
# Create your views here.
