from rest_framework import viewsets
from .models import Part
from .serializers import PartSerializer

class PartViewSet(viewsets.ModelViewSet):
    queryset = Part.objects.all()
    serializer_class = PartSerializer