from rest_framework import serializers
from .models import BotUser, BotMessageLog, ReminderSettings, UnknownPlateSearch

class BotUserSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    
    class Meta:
        model = BotUser
        fields = '__all__'

class MessageLogSerializer(serializers.ModelSerializer):
    bot_user_name = serializers.SerializerMethodField()

    def get_bot_user_name(self, obj):
        if obj.bot_user:
            parts = [obj.bot_user.first_name, obj.bot_user.last_name]
            full_name = ' '.join(p for p in parts if p)
            return full_name or '-'
        return '-'

    class Meta:
        model = BotMessageLog  # Використовуємо правильну модель
        fields = '__all__'

class ReminderSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReminderSettings
        fields = '__all__'


class UnknownPlateSearchSerializer(serializers.ModelSerializer):
    last_searched_by_name = serializers.SerializerMethodField()

    def get_last_searched_by_name(self, obj):
        if not obj.last_searched_by:
            return None
        u = obj.last_searched_by
        parts = [u.first_name, u.last_name]
        full_name = ' '.join(p for p in parts if p)
        return full_name or u.username or str(u.telegram_id)

    class Meta:
        model = UnknownPlateSearch
        fields = [
            'id', 'plate', 'search_count',
            'first_searched_at', 'last_searched_at',
            'last_searched_by', 'last_searched_by_name',
            'notes',
        ]
        read_only_fields = [
            'plate', 'search_count',
            'first_searched_at', 'last_searched_at',
            'last_searched_by', 'last_searched_by_name',
        ]