# bot/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import BotUser, BotMessageLog


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = (
        'get_full_name_display',
        'chat_id',
        'role',
        'client',
        'phone_number',
        'is_active',
        'is_blocked',
        'last_activity'
    )
    list_filter = ('role', 'is_active', 'is_blocked', 'notifications_enabled')
    search_fields = (
        'chat_id',
        'username',
        'first_name',
        'last_name',
        'phone_number',
        'client__name'
    )
    list_editable = ('role', 'is_active', 'is_blocked')
    readonly_fields = ('chat_id', 'created_at', 'last_activity')
    
    filter_horizontal = ('allowed_trucks',)
    autocomplete_fields = ['client']
    
    fieldsets = (
        ('Основна інформація', {
            'fields': (
                'chat_id',
                'username',
                'first_name',
                'last_name',
                'phone_number'
            )
        }),
        ('Роль та доступи', {
            'fields': (
                'role',
                'client',
                'allowed_trucks',
            ),
            'description': (
                '<strong>Адміністратор</strong>: повний доступ до всього<br>'
                '<strong>Власник</strong>: доступ до всіх авто свого клієнта<br>'
                '<strong>Водій</strong>: доступ тільки до вибраних авто<br>'
                '<strong>Гість</strong>: обмежений доступ'
            )
        }),
        ('Сповіщення', {
            'fields': (
                'notifications_enabled',
                'notify_order_status',
                'notify_maintenance'
            ),
            'classes': ('collapse',)
        }),
        ('Статус', {
            'fields': (
                'is_active',
                'is_blocked',
                'created_at',
                'last_activity'
            )
        }),
    )
    
    def get_full_name_display(self, obj):
        """Відображення імені з кольором ролі"""
        colors = {
            'admin': '#d32f2f',
            'owner': '#1976d2',
            'driver': '#388e3c',
            'guest': '#757575',
        }
        color = colors.get(obj.role, '#000')
        
        icon = '👑' if obj.role == 'admin' else '👤'
        name = obj.full_name
        
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color,
            icon,
            name
        )
    get_full_name_display.short_description = 'Користувач'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('client')
    
    actions = ['block_users', 'unblock_users', 'enable_notifications', 'disable_notifications']
    
    @admin.action(description='Заблокувати вибраних користувачів')
    def block_users(self, request, queryset):
        queryset.update(is_blocked=True)
    
    @admin.action(description='Розблокувати вибраних користувачів')
    def unblock_users(self, request, queryset):
        queryset.update(is_blocked=False)
    
    @admin.action(description='Увімкнути сповіщення')
    def enable_notifications(self, request, queryset):
        queryset.update(notifications_enabled=True)
    
    @admin.action(description='Вимкнути сповіщення')
    def disable_notifications(self, request, queryset):
        queryset.update(notifications_enabled=False)


@admin.register(BotMessageLog)
class BotMessageLogAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'phone_number', 'chat_id', 'message_text_short', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user_name', 'phone_number', 'message_text', 'bot_response', 'chat_id')
    readonly_fields = ('chat_id', 'user_name', 'phone_number', 'message_text', 'bot_response', 'created_at')
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def message_text_short(self, obj):
        """Скорочений текст повідомлення"""
        text = obj.message_text[:50]
        if len(obj.message_text) > 50:
            text += '...'
        return text
    message_text_short.short_description = 'Повідомлення'