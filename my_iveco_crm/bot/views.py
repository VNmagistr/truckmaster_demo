# bot/views.py

from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import BotUser, BotMessageLog, ReminderSettings
from .serializers import (
    BotUserSerializer, MessageLogSerializer, ReminderSettingsSerializer
)


class BotUserViewSet(viewsets.ModelViewSet):
    """API для користувачів бота"""
    queryset = BotUser.objects.select_related('client').prefetch_related('assigned_trucks')
    serializer_class = BotUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active', 'is_blocked']
    search_fields = ['username', 'first_name', 'last_name', 'phone_number']
    ordering_fields = ['created_at', 'last_activity']
    ordering = ['-last_activity']
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Статистика по користувачах"""
        from django.db.models import Count
        
        stats = {
            'total': BotUser.objects.count(),
            'by_role': dict(
                BotUser.objects.values('role').annotate(count=Count('id')).values_list('role', 'count')
            ),
            'active': BotUser.objects.filter(is_active=True).count(),
            'blocked': BotUser.objects.filter(is_blocked=True).count(),
        }
        return Response(stats)


class MessageLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API для логів повідомлень (тільки читання)"""
    queryset = BotMessageLog.objects.select_related('bot_user').all()
    serializer_class = MessageLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['bot_user', 'message_type', 'is_incoming', 'is_processed']
    search_fields = ['message_text', 'bot_response']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Останні 15 повідомлень (для адмінів)"""
        recent_messages = self.queryset[:15]
        serializer = self.get_serializer(recent_messages, many=True)
        return Response(serializer.data)


class ReminderSettingsViewSet(viewsets.ModelViewSet):
    """API для налаштувань нагадувань"""
    queryset = ReminderSettings.objects.select_related('bot_user', 'truck').all()
    serializer_class = ReminderSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['bot_user', 'truck', 'reminder_type', 'is_enabled']