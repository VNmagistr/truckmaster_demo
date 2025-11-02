from django.contrib import admin
from .models import BotMessageLog

@admin.register(BotMessageLog)
class BotMessageLogAdmin(admin.ModelAdmin):
    # Додаємо 'phone_number' у список
    list_display = ('user_name', 'phone_number', 'chat_id', 'message_text', 'bot_response', 'created_at')
    list_filter = ('user_name', 'created_at')
    search_fields = ('user_name', 'phone_number', 'message_text', 'bot_response')
    # Додаємо 'phone_number' у поля "тільки для читання"
    readonly_fields = ('chat_id', 'user_name', 'phone_number', 'message_text', 'bot_response', 'created_at')

    def has_add_permission(self, request):
        return False 

    def has_change_permission(self, request, obj=None):
        return False