from rest_framework import serializers
from .models import BotUser, BotMessageLog, ReminderSettings

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