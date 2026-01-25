from rest_framework import serializers
from .models import BotUser, BotMessageLog, ReminderSettings

class BotUserSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    
    class Meta:
        model = BotUser
        fields = '__all__'

class MessageLogSerializer(serializers.ModelSerializer):
    bot_user_name = serializers.CharField(source='bot_user.get_full_name', read_only=True, default='-')

    class Meta:
        model = BotMessageLog  # Використовуємо правильну модель
        fields = '__all__'

class ReminderSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReminderSettings
        fields = '__all__'