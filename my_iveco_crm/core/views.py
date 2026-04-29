# core/views.py

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Module
from .serializers import ModuleSerializer


class ModuleListView(APIView):
    """
    GET  /api/modules/  — список усіх модулів (тільки адміністратор).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        modules = Module.objects.all()
        return Response(ModuleSerializer(modules, many=True).data)


class EnumsView(APIView):
    """
    GET /api/enums/ — довідник choices з моделей (єдине джерело істини для фронту).
    Дозволяє не дублювати списки в src/utils/constants.js.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from clients.models import Truck
        from orders.models import TruckMaintenanceIntervals

        def _to_options(choices):
            return [{'value': v, 'label': l} for v, l in choices]

        return Response({
            'euro_standards':     _to_options(Truck.EURO_STANDARD_CHOICES),
            'transmission_types': _to_options(Truck.TRANSMISSION_CHOICES),
            'tracking_modes':     _to_options(TruckMaintenanceIntervals.TrackingMode.choices),
        })
