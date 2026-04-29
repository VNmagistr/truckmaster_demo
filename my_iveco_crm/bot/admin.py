from django.contrib import admin
from .models import BotUser, BotMessageLog, MileageReport, BotSettings, UnknownPlateSearch

@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'role', 'client', 'phone_number', 'is_active')
    list_filter = ('role', 'is_active', 'is_blocked')
    search_fields = ('username', 'first_name', 'last_name', 'phone_number', 'client__name')
    autocomplete_fields = ['client']
    filter_horizontal = ('assigned_trucks',)
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


@admin.register(MileageReport)
class MileageReportAdmin(admin.ModelAdmin):
    list_display = ('truck', 'mileage', 'bot_user', 'reported_at')
    list_filter = ('reported_at',)
    search_fields = ('truck__license_plate', 'bot_user__first_name')
    readonly_fields = ('bot_user', 'truck', 'mileage', 'reported_at')


@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    fields = ('ask_mileage_enabled',)

    def has_add_permission(self, request):
        return not BotSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UnknownPlateSearch)
class UnknownPlateSearchAdmin(admin.ModelAdmin):
    list_display = ('plate', 'search_count', 'last_searched_at', 'last_searched_by', 'notes')
    list_filter = ('last_searched_at',)
    search_fields = ('plate', 'notes')
    readonly_fields = ('plate', 'search_count', 'first_searched_at', 'last_searched_at', 'last_searched_by')