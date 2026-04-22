from django.contrib import admin
from django.utils.html import format_html

from .models import ShortLink


@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin):
    list_display = ('slug', 'target_link', 'label', 'is_active', 'hits', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('slug', 'target_url', 'label')
    readonly_fields = ('hits', 'created_at', 'updated_at')
    fields = ('slug', 'target_url', 'label', 'is_active', 'hits', 'created_at', 'updated_at')

    @admin.display(description='Target URL')
    def target_link(self, obj):
        return format_html(
            '<a href="{0}" target="_blank" rel="noopener noreferrer">{0}</a>',
            obj.target_url,
        )
