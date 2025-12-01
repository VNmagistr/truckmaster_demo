# bot/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import BotUser, BotMessageLog, BotSettings, SentReminder


@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    """
    Глобальні налаштування бота
    """
    list_display = ['get_status', 'reminder_km_before', 'reminder_days_before', 'reminder_time', 'last_check']
    
    fieldsets = (
        ('🔔 Нагадування про ТО', {
            'fields': ('maintenance_reminders_enabled', 'reminder_km_before', 'reminder_days_before', 'reminder_time'),
            'description': '⚠️ УВАГА: Це глобальні налаштування для всієї системи нагадувань'
        }),
        ('📊 Системна інформація', {
            'fields': ('last_check',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['last_check']
    
    def get_status(self, obj):
        if obj.maintenance_reminders_enabled:
            return format_html('<span style="color: green; font-weight: bold;">✅ УВІМКНЕНО</span>')
        return format_html('<span style="color: red; font-weight: bold;">❌ ВИМКНЕНО</span>')
    get_status.short_description = 'Статус нагадувань'
    
    def has_add_permission(self, request):
        # Дозволяємо тільки один запис
        return not BotSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Не дозволяємо видаляти
        return False


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = [
        'get_name_with_emoji', 
        'username', 
        'get_role_colored', 
        'client',
        'get_reminders_status',
        'is_active', 
        'last_activity'
    ]
    list_filter = [
        'role', 
        'is_active', 
        'is_blocked',
        'enable_maintenance_reminders',
        'reminder_telegram_enabled'
    ]
    search_fields = ['chat_id', 'username', 'first_name', 'last_name', 'phone_number']
    # readonly_fields = ['last_activity', 'created_at']
    filter_horizontal = ['allowed_trucks']
    def get_readonly_fields(self, request, obj=None):
        """
        Chat ID readonly тільки при редагуванні існуючого користувача.
        При створенні нового - можна вказати.
        """
        if obj:  # Редагування існуючого
            return ['chat_id', 'last_activity', 'created_at']
        else:  # Створення нового
            return ['last_activity', 'created_at']
    
    fieldsets = (
        ('👤 Особиста інформація', {
            'fields': ('chat_id', 'username', 'first_name', 'last_name', 'phone_number')
        }),
        ('🎭 Роль та права', {
            'fields': ('role', 'client', 'allowed_trucks')
        }),
        ('🔔 Налаштування нагадувань', {
            'fields': ('enable_maintenance_reminders', 'reminder_telegram_enabled'),
            'description': 'Персональні налаштування нагадувань для цього користувача'
        }),
        ('🔒 Статус', {
            'fields': ('is_active', 'is_blocked', 'notes')
        }),
        ('📅 Системна інформація', {
            'fields': ('created_at', 'last_activity'),
            'classes': ('collapse',)
        }),
    )
    
    def get_reminders_status(self, obj):
        """Показує статус нагадувань"""
        if obj.enable_maintenance_reminders and obj.reminder_telegram_enabled:
            return format_html('<span style="color: green;">✅ Увімкнено</span>')
        elif obj.enable_maintenance_reminders:
            return format_html('<span style="color: orange;">⚠️ Частково</span>')
        return format_html('<span style="color: red;">❌ Вимкнено</span>')
    get_reminders_status.short_description = 'Нагадування'
    
    def get_name_with_emoji(self, obj):
        emoji = obj.get_role_emoji()
        return f"{emoji} {obj.first_name} {obj.last_name}".strip()
    get_name_with_emoji.short_description = 'Ім\'я'
    
    def get_role_colored(self, obj):
        colors = {
            'admin': '#ff6b6b',
            'owner': '#4ecdc4',
            'driver': '#95e1d3',
            'guest': '#cccccc'
        }
        color = colors.get(obj.role, '#000000')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_role_display()
        )
    get_role_colored.short_description = 'Роль'


@admin.register(SentReminder)
class SentReminderAdmin(admin.ModelAdmin):
    list_display = [
        'sent_at',
        'bot_user', 
        'truck', 
        'reminder_type',
        'get_delivery_status',
        'service_reminder'
    ]
    list_filter = ['reminder_type', 'delivery_status', 'sent_at']
    search_fields = ['bot_user__first_name', 'truck__license_plate']
    readonly_fields = ['sent_at', 'error_message']
    date_hierarchy = 'sent_at'
    
    fieldsets = (
        ('📤 Нагадування', {
            'fields': ('bot_user', 'truck', 'service_reminder', 'reminder_type')
        }),
        ('📊 Статус доставки', {
            'fields': ('delivery_status', 'error_message', 'sent_at')
        }),
    )
    
    def get_delivery_status(self, obj):
        colors = {
            'sent': 'blue',
            'delivered': 'green',
            'failed': 'red'
        }
        color = colors.get(obj.delivery_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_delivery_status_display()
        )
    get_delivery_status.short_description = 'Статус'
    
    def has_add_permission(self, request):
        return False  # Створюються автоматично


@admin.register(BotMessageLog)
class BotMessageLogAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'phone_number', 'chat_id', 'message_text', 'bot_response', 'created_at')
    list_filter = ('user_name', 'created_at')
    search_fields = ('user_name', 'phone_number', 'message_text', 'bot_response')
    readonly_fields = ('chat_id', 'user_name', 'phone_number', 'message_text', 'bot_response', 'created_at')

    def has_add_permission(self, request):
        return False 

    def has_change_permission(self, request, obj=None):
        return False