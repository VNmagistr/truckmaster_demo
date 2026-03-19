# core/admin.py

from django.contrib import admin
from django.utils.html import format_html

from .models import Module


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['label', 'name', 'status_badge', 'is_core', 'deps_display', 'updated_at']
    list_editable = []  # редагування через форму, щоб тригерити save() і очищати кеш
    list_filter = ['is_enabled', 'is_core']
    ordering = ['order', 'name']
    readonly_fields = ['name', 'is_core', 'url_prefixes', 'dependencies', 'order', 'updated_at']

    fieldsets = (
        (None, {
            'fields': ('name', 'label', 'description', 'is_enabled'),
        }),
        ('Технічні дані', {
            'fields': ('is_core', 'url_prefixes', 'dependencies', 'order', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        fields = list(self.readonly_fields)
        if obj and obj.is_core:
            fields.append('is_enabled')
        return fields

    @admin.display(description='Стан')
    def status_badge(self, obj):
        if obj.is_core:
            return format_html(
                '<span style="color:#888; font-weight:bold;">⚙ Базовий</span>'
            )
        if obj.is_enabled:
            return format_html(
                '<span style="color:green; font-weight:bold;">✔ Увімкнено</span>'
            )
        return format_html(
            '<span style="color:red; font-weight:bold;">✘ Вимкнено</span>'
        )

    @admin.display(description='Залежності')
    def deps_display(self, obj):
        if not obj.dependencies:
            return '—'
        return ', '.join(obj.dependencies)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
