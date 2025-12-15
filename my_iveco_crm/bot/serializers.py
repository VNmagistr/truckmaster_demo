# bot/serializers.py

from rest_framework import serializers
from .models import BotUser, BotMessageLog, ReminderSettings, SentReminder


class BotUserSerializer(serializers.ModelSerializer):
    """Серіалізатор для користувачів бота"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = BotUser
        fields = [
            'id', 'telegram_id', 'username', 'first_name', 'last_name',
            'phone_number', 'role', 'role_display', 'client', 'client_name',
            'assigned_trucks', 'is_active', 'is_blocked', 'notifications_enabled',
            'total_messages', 'last_activity', 'created_at'
        ]
        read_only_fields = ['telegram_id', 'total_messages', 'last_activity', 'created_at']


class MessageLogSerializer(serializers.ModelSerializer):
    """Серіалізатор для логів повідомлень"""
    bot_user_name = serializers.CharField(source='bot_user.get_full_name', read_only=True)
    message_type_display = serializers.CharField(source='get_message_type_display', read_only=True)
    
    class Meta:
        model = BotMessageLog
        fields = [
            'id', 'bot_user', 'bot_user_name', 'message_type', 'message_type_display',
            'is_incoming', 'message_text', 'bot_response', 'is_processed',
            'processing_time_ms', 'handler_name', 'error_message', 'created_at'
        ]
        read_only_fields = ['created_at']


class ReminderSettingsSerializer(serializers.ModelSerializer):
    """Серіалізатор для налаштувань нагадувань"""
    bot_user_name = serializers.CharField(source='bot_user.get_full_name', read_only=True)
    truck_info = serializers.SerializerMethodField()
    reminder_type_display = serializers.CharField(source='get_reminder_type_display', read_only=True)
    
    class Meta:
        model = ReminderSettings
        fields = [
            'id', 'bot_user', 'bot_user_name', 'truck', 'truck_info',
            'reminder_type', 'reminder_type_display', 'is_enabled',
            'advance_days', 'advance_km', 'notify_time', 'repeat_days'
        ]
    
    def get_truck_info(self, obj):
        if obj.truck:
            return {
                'id': obj.truck.id,
                'license_plate': obj.truck.license_plate,
                'model': obj.truck.specific_model_name
            }
        return None


class SentReminderSerializer(serializers.ModelSerializer):
    """Серіалізатор для відправлених нагадувань"""
    bot_user_name = serializers.CharField(source='bot_user.get_full_name', read_only=True)
    
    class Meta:
        model = SentReminder
        fields = [
            'id', 'bot_user', 'bot_user_name', 'truck', 'reminder_type',
            'message_text', 'is_delivered', 'delivery_error', 'is_read',
            'user_action', 'sent_at'
        ]
        read_only_fields = ['sent_at']