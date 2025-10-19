from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from rest_framework.parsers import MultiPartParser, FormParser
from .models import ServiceOrder, ServiceWork, Employee, WorkCategory, Work, RepairPhoto
from inventory.models import UsedPart 
from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework import exceptions
import logging # Додаємо логування

# Отримуємо логгер
logger = logging.getLogger(__name__)

from .serializers import (
    RepairPhotoSerializer,
    ServiceOrderListSerializer, 
    ServiceOrderDetailSerializer,
    ServiceOrderWriteSerializer,
    ServiceWorkWriteSerializer,
    UsedPartSerializer,
    EmployeeSerializer,
    WorkCategorySerializer
)

class IsBotAuthenticated(BasePermission):
    """
    Дозволяє доступ, тільки якщо в заголовку є правильний секретний ключ.
    """
    def has_permission(self, request, view):
        secret = request.headers.get('X-Bot-Api-Secret')
        if not secret or secret != settings.BOT_API_SECRET_KEY:
            raise exceptions.AuthenticationFailed('Неправильний токен бота')
        return True


class BotOrderStatusView(APIView):
    """
    Безпечний ендпоінт для бота, щоб отримати статус замовлення.
    """
    permission_classes = [IsBotAuthenticated]

    def get(self, request, order_number, format=None):
        try:
            order = ServiceOrder.objects.select_related('client', 'truck').get(order_number=order_number)
            serializer = ServiceOrderListSerializer(order)
            return Response(serializer.data)
        
        except ServiceOrder.DoesNotExist:
            # Це очікувана помилка, якщо номер не знайдено
            return Response({'detail': 'Not Found'}, status=404)
        
        except Exception as e:
            # --- ДОДАНО: Обробляємо всі інші помилки ---
            # Наприклад, якщо `order_number` буде "привіт" і викличе 'ValidationError'
            logger.error(f"Bot API Error: Не вдалося обробити запит на номер {order_number}. Помилка: {e}")
            return Response({'detail': 'Bad Request'}, status=400)


class DashboardOrderStatsView(APIView):
    """
    Повертає статистику по замовленнях за різні періоди з порівнянням.
    """
    def get(self, request, format=None):
        now = timezone.now()
        
        start_of_week = now.date() - timedelta(days=now.weekday())
        start_of_month = now.date().replace(day=1)
        start_of_year = now.date().replace(month=1, day=1)

        last_year_now = now.replace(year=now.year - 1)
        start_of_week_ly = last_year_now.date() - timedelta(days=last_year_now.weekday())
        end_of_week_ly = start_of_week_ly + timedelta(days=6)
        start_of_month_ly = last_year_now.date().replace(day=1)
        end_of_month_ly = (start_of_month_ly + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        start_of_year_ly = last_year_now.date().replace(month=1, day=1)
        end_of_year_ly = last_year_now.date().replace(month=12, day=31)

        stats = {
            'this_week': ServiceOrder.objects.filter(start_date__gte=start_of_week).count(),
            'this_month': ServiceOrder.objects.filter(start_date__gte=start_of_month).count(),
            'this_year': ServiceOrder.objects.filter(start_date__gte=start_of_year).count(),
            'compare_week': ServiceOrder.objects.filter(start_date__range=(start_of_week_ly, end_of_week_ly)).count(),
            'compare_month': ServiceOrder.objects.filter(start_date__range=(start_of_month_ly, end_of_month_ly)).count(),
            'compare_year': ServiceOrder.objects.filter(start_date__range=(start_of_year_ly, end_of_year_ly)).count(),
        }
        return Response(stats)


class ServiceOrderViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrder.objects.select_related('client', 'truck').all()
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']
    parser_classes = (MultiPartParser, FormParser)

    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceOrderListSerializer
        
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceOrderWriteSerializer
        
        return ServiceOrderDetailSerializer

class RecentOrdersViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceOrder.objects.order_by('-start_date')[:5]
    serializer_class = ServiceOrderListSerializer

class WorkCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WorkCategory.objects.prefetch_related('works').all()
    serializer_class = WorkCategorySerializer

class ServiceWorkViewSet(viewsets.ModelViewSet):
    queryset = ServiceWork.objects.all()
    serializer_class = ServiceWorkWriteSerializer

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

class UsedPartViewSet(viewsets.ModelViewSet):
    queryset = UsedPart.objects.all()
    serializer_class = UsedPartSerializer

class RepairPhotoViewSet(viewsets.ModelViewSet):
    queryset = RepairPhoto.objects.all()
    serializer_class = RepairPhotoSerializer