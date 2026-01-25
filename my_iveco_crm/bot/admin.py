from django.contrib import admin
from .models import BotUser, BotMessageLog, ReminderSettings

@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'role', 'client', 'phone_number', 'is_active')
    list_filter = ('role', 'is_active', 'is_blocked')
    search_fields = ('username', 'first_name', 'last_name', 'phone_number', 'client__name')
    autocomplete_fields = ['client']
    readonly_fields = ('created_at', 'last_activity')
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('telegram_id', 'username', 'first_name', 'last_name', 'phone_number', 'language_code')
        }),
        ('Прив\'язка та Роль', {
            'fields': ('client', 'role', 'assigned_trucks')
        }),
        ('Статус', {
            'fields': ('is_active', 'is_blocked')
        }),
        ('Дати', {
            'fields': ('created_at', 'last_activity')
        }),
    )

@admin.register(BotMessageLog)
class BotMessageLogAdmin(admin.ModelAdmin):
    list_display = ('bot_user', 'message_text_preview', 'is_incoming', 'created_at')
    list_filter = ('is_incoming', 'message_type', 'created_at')
    search_fields = ('bot_user__first_name', 'bot_user__last_name', 'message_text', 'bot_response')
    readonly_fields = ('bot_user', 'message_type', 'is_incoming', 'message_text', 'bot_response', 'created_at', 'is_processed')
    
    def message_text_preview(self, obj):
        return obj.message_text[:50] + "..." if len(obj.message_text) > 50 else obj.message_text
    message_text_preview.short_description = "Текст"

@admin.register(ReminderSettings)
class ReminderSettingsAdmin(admin.ModelAdmin):
    list_display = ('bot_user', 'truck', 'reminder_type', 'is_enabled')
    list_filter = ('is_enabled', 'reminder_type')
    search_fields = ('bot_user__first_name', 'truck__license_plate')
    autocomplete_fields = ['bot_user', 'truck']