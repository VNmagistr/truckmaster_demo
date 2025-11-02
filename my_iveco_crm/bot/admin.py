from django.contrib import admin
from .models import BotMessageLog

@admin.register(BotMessageLog)
class BotMessageLogAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'chat_id', 'message_text', 'bot_response', 'created_at')
    list_filter = ('user_name', 'created_at')
    search_fields = ('user_name', 'message_text', 'bot_response')
    readonly_fields = ('created_at',) # Поля, які не можна редагувати

    def has_add_permission(self, request):
        return False # Забороняємо створювати логи вручну

    def has_change_permission(self, request, obj=None):
        return False # Забороняємо редагувати логи