# bot/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count

from .models import (
    BotUser, ConversationState, BotMessageLog, 
    ReminderSettings, SentReminder, BotCommand
)


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = (
        'telegram_id', 'get_name', 'role', 'phone_number', 
        'is_active', 'is_blocked', 'total_messages', 'last_activity'
    )
    list_filter = ('role', 'is_active', 'is_blocked', 'notifications_enabled', 'created_at')
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name', 'phone_number')
    readonly_fields = ('telegram_id', 'total_messages', 'created_at', 'updated_at', 'last_activity')
    
    autocomplete_fields = ['client', 'assigned_trucks']
    filter_horizontal = ('assigned_trucks',)
    
    fieldsets = (
        ('Telegram дані', {
            'fields': ('telegram_id', 'username', 'first_name', 'last_name')
        }),
        ('Контакти', {
            'fields': ('phone_number',)
        }),
        ('Роль та доступ', {
            'fields': ('role', 'client', 'assigned_trucks')
        }),
        ('Статус', {
            'fields': ('is_active', 'is_blocked', 'block_reason')
        }),
        ('Налаштування', {
            'fields': ('language_code', 'notifications_enabled')
        }),
        ('Статистика', {
            'fields': ('total_messages', 'last_activity', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['block_users', 'unblock_users', 'promote_to_owner', 'promote_to_driver']
    
    def get_name(self, obj):
        """Відображає ім'я з лінком на Telegram"""
        name = obj.get_full_name()
        if obj.username:
            telegram_link = f"https://t.me/{obj.username}"
            return format_html('<a href="{}" target="_blank">{}  🔗</a>', telegram_link, name)
        return name
    get_name.short_description = "Ім'я"
    
    @admin.action(description='Заблокувати користувачів')
    def block_users(self, request, queryset):
        queryset.update(is_blocked=True, block_reason="Заблоковано адміністратором")
        self.message_user(request, f"Заблоковано {queryset.count()} користувачів")
    
    @admin.action(description='Розблокувати користувачів')
    def unblock_users(self, request, queryset):
        queryset.update(is_blocked=False, block_reason="")
        self.message_user(request, f"Розблоковано {queryset.count()} користувачів")
    
    @admin.action(description='Призначити роль "Власник"')
    def promote_to_owner(self, request, queryset):
        queryset.update(role='owner')
        self.message_user(request, f"Призначено роль власника {queryset.count()} користувачам")
    
    @admin.action(description='Призначити роль "Водій"')
    def promote_to_driver(self, request, queryset):
        queryset.update(role='driver')
        self.message_user(request, f"Призначено роль водія {queryset.count()} користувачам")


@admin.register(ConversationState)
class ConversationStateAdmin(admin.ModelAdmin):
    list_display = ('bot_user', 'current_state', 'updated_at')
    list_filter = ('current_state', 'updated_at')
    search_fields = ('bot_user__telegram_id', 'bot_user__username', 'bot_user__first_name')
    readonly_fields = ('updated_at',)
    
    def has_add_permission(self, request):
        """Заборона ручного створення - створюється автоматично"""
        return False


@admin.register(BotMessageLog)
class BotMessageLogAdmin(admin.ModelAdmin):
    list_display = (
        'created_at', 'get_user_info', 'message_type', 'direction', 
        'get_message_preview', 'is_processed', 'processing_time_ms'
    )
    list_filter = (
        'message_type', 'is_incoming', 'is_processed', 'created_at',
        ('bot_user__role', admin.ChoicesFieldListFilter),
    )
    search_fields = (
        'bot_user__telegram_id', 'bot_user__username', 
        'bot_user__first_name', 'message_text', 'bot_response'
    )
    readonly_fields = (
        'bot_user', 'message_type', 'is_incoming', 'message_text',
        'message_data', 'bot_response', 'is_processed', 'processing_time_ms',
        'handler_name', 'error_message', 'created_at'
    )
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Користувач', {
            'fields': ('bot_user',)
        }),
        ('Повідомлення', {
            'fields': ('message_type', 'is_incoming', 'message_text', 'message_data')
        }),
        ('Відповідь бота', {
            'fields': ('bot_response',)
        }),
        ('Обробка', {
            'fields': ('is_processed', 'processing_time_ms', 'handler_name', 'error_message')
        }),
        ('Час', {
            'fields': ('created_at',)
        }),
    )
    
    def has_add_permission(self, request):
        """Заборона ручного створення - створюється автоматично"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Тільки перегляд"""
        return False
    
    def get_user_info(self, obj):
        """Інформація про користувача"""
        username = f"@{obj.bot_user.username}" if obj.bot_user.username else ""
        phone = obj.bot_user.phone_number or ""
        return format_html(
            '<strong>{}</strong><br><small>{} {}</small>',
            obj.bot_user.get_full_name(),
            username,
            phone
        )
    get_user_info.short_description = "Користувач"
    
    def direction(self, obj):
        """Напрямок повідомлення"""
        if obj.is_incoming:
            return format_html('<span style="color: blue;">➡️ Вхідне</span>')
        return format_html('<span style="color: green;">⬅️ Вихідне</span>')
    direction.short_description = "Напрямок"
    
    def get_message_preview(self, obj):
        """Попередній перегляд повідомлення"""
        text = obj.message_text if obj.is_incoming else obj.bot_response
        if len(text) > 80:
            return text[:80] + '...'
        return text
    get_message_preview.short_description = "Повідомлення"


@admin.register(ReminderSettings)
class ReminderSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'bot_user', 'truck', 'reminder_type', 'is_enabled',
        'advance_days', 'advance_km', 'notify_time'
    )
    list_filter = ('reminder_type', 'is_enabled', 'bot_user__role')
    search_fields = (
        'bot_user__username', 'bot_user__first_name',
        'truck__license_plate', 'truck__last_seven_vin'
    )
    autocomplete_fields = ['bot_user', 'truck']
    
    fieldsets = (
        ('Користувач та автомобіль', {
            'fields': ('bot_user', 'truck')
        }),
        ('Тип нагадування', {
            'fields': ('reminder_type', 'is_enabled')
        }),
        ('Налаштування часу', {
            'fields': ('advance_days', 'advance_km', 'notify_time', 'repeat_days')
        }),
    )


@admin.register(SentReminder)
class SentReminderAdmin(admin.ModelAdmin):
    list_display = (
        'sent_at', 'bot_user', 'truck', 'reminder_type',
        'is_delivered', 'is_read', 'user_action'
    )
    list_filter = ('reminder_type', 'is_delivered', 'is_read', 'sent_at')
    search_fields = (
        'bot_user__username', 'bot_user__first_name',
        'truck__license_plate', 'message_text'
    )
    readonly_fields = (
        'bot_user', 'truck', 'reminder_type', 'message_text',
        'is_delivered', 'delivery_error', 'is_read', 'user_action', 'sent_at'
    )
    date_hierarchy = 'sent_at'
    
    def has_add_permission(self, request):
        """Заборона ручного створення"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Тільки перегляд"""
        return False


@admin.register(BotCommand)
class BotCommandAdmin(admin.ModelAdmin):
    list_display = (
        'command', 'description', 'required_role',
        'usage_count', 'is_active', 'last_used'
    )
    list_filter = ('required_role', 'is_active')
    search_fields = ('command', 'description')
    readonly_fields = ('usage_count', 'last_used')
    
    fieldsets = (
        ('Команда', {
            'fields': ('command', 'description', 'required_role')
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
        ('Статистика', {
            'fields': ('usage_count', 'last_used'),
            'classes': ('collapse',)
        }),
    )