from django.contrib import admin
from django.utils.html import format_html

from .models import Client, ClientFeature, IvecoBaseModel, Truck, OwnershipHistory


# ── ClientFeature inline ──────────────────────────────────────────────────────

class ClientFeatureInline(admin.StackedInline):
    model = ClientFeature
    can_delete = False
    verbose_name = 'Доступ до функцій'
    verbose_name_plural = 'Доступ до функцій'
    fields = [
        'cabinet',
        'bot',
        'invoices',
        'appointments',
        'notifications_telegram',
        'notifications_whatsapp',
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('client')


# ── Client admin ──────────────────────────────────────────────────────────────

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    change_form_template = 'admin/clients/client/change_form.html'

    list_display = ('name', 'phone', 'email', 'features_summary', 'is_admin')
    list_editable = ('is_admin',)
    search_fields = ('name', 'phone', 'email')
    inlines = [ClientFeatureInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Гарантуємо, що ClientFeature існує
        ClientFeature.objects.get_or_create(client=obj)

    @admin.display(description='Функції')
    def features_summary(self, obj):
        try:
            f = obj.features
        except ClientFeature.DoesNotExist:
            return format_html('<span style="color:#aaa">—</span>')

        icons = []
        if f.cabinet:
            icons.append(('<span title="Кабінет">🗂</span>'))
        if f.bot:
            icons.append('<span title="Telegram бот">🤖</span>')
        if f.invoices:
            icons.append('<span title="Рахунки">🧾</span>')
        if f.appointments:
            icons.append('<span title="Онлайн-запис">📅</span>')
        if f.notifications_telegram:
            icons.append('<span title="Сповіщення Telegram">📨</span>')
        if f.notifications_whatsapp:
            icons.append('<span title="Сповіщення WhatsApp">💬</span>')

        if not icons:
            return format_html('<span style="color:#cc0000">✘ Без доступу</span>')

        return format_html(' '.join(icons))


# ── Інші моделі ───────────────────────────────────────────────────────────────

@admin.register(IvecoBaseModel)
class IvecoBaseModelAdmin(admin.ModelAdmin):
    search_fields = ('name',)


class OwnershipHistoryInline(admin.TabularInline):
    model = OwnershipHistory
    extra = 0
    readonly_fields = ('client', 'license_plate', 'change_date')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = (
        'license_plate',
        'client',
        'specific_model_name',
        'euro_standard',
        'last_seven_vin',
        'colored_vin',
    )
    search_fields = ('license_plate', 'last_seven_vin', 'client__name', 'specific_model_name', 'full_vin')
    list_filter = ('client', 'base_model', 'euro_standard')
    autocomplete_fields = ('client', 'base_model')
    readonly_fields = ('last_seven_vin',)

    fieldsets = (
        ('Основна інформація', {
            'fields': ('client', 'base_model', 'specific_model_name', 'euro_standard')
        }),
        ('VIN код', {
            'fields': ('full_vin', 'last_seven_vin'),
            'description': 'Останні 7 символів розраховуються автоматично'
        }),
        ('Реєстрація', {
            'fields': ('license_plate',)
        }),
    )

    inlines = [OwnershipHistoryInline]

    def colored_vin(self, obj):
        if obj.full_vin.startswith('XXXXXXXX') or obj.full_vin.startswith('TEMP'):
            return format_html(
                '<span style="background-color:#ffcccc;color:#cc0000;font-weight:bold;'
                'padding:3px 8px;border-radius:3px;display:inline-block;">⚠️ {}</span>',
                obj.full_vin,
            )
        return format_html('<span style="color:#28a745">{}</span>', obj.full_vin)

    colored_vin.short_description = 'VIN код (повний)'
    colored_vin.admin_order_field = 'full_vin'

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        client_id = request.GET.get('client_id')
        referer = request.META.get('HTTP_REFERER', '')
        if not client_id and 'serviceorder' in referer.lower():
            forward = request.GET.get('forward')
            if forward:
                import json
                try:
                    forward_data = json.loads(forward)
                    client_id = forward_data.get('client')
                except (json.JSONDecodeError, TypeError):
                    pass
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        return queryset, use_distinct
