# core/views.py

from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Module
from .serializers import ModuleSerializer


class ModuleListView(APIView):
    """
    GET  /api/modules/  — список усіх модулів (тільки адміністратор).
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        modules = Module.objects.all()
        return Response(ModuleSerializer(modules, many=True).data)
