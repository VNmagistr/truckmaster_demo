from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from .models import ShortLink


@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin):
    list_display = ('slug', 'target_link', 'label', 'is_active', 'has_qr', 'hits', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('slug', 'target_url', 'label')
    readonly_fields = ('hits', 'created_at', 'updated_at', 'qr_preview')
    fields = ('slug', 'target_url', 'label', 'is_active', 'hits', 'created_at', 'updated_at', 'qr_preview')
    actions = ['generate_qr_bulk']

    @admin.display(description='Target URL')
    def target_link(self, obj):
        return format_html(
            '<a href="{0}" target="_blank" rel="noopener noreferrer">{0}</a>',
            obj.target_url,
        )

    @admin.display(description='QR', boolean=True)
    def has_qr(self, obj):
        return bool(obj.qr_svg)

    @admin.display(description='QR-код')
    def qr_preview(self, obj):
        if not obj.pk:
            return 'Збережіть запис, щоб згенерувати QR-код.'

        parts = []

        if obj.qr_svg:
            parts.append(
                f'<div style="background:#fff;display:inline-block;padding:12px;'
                f'border:1px solid #ccc;border-radius:4px;margin-bottom:12px">'
                f'{obj.qr_svg}</div><br>'
                f'<code>{obj.full_url}</code><br><br>'
            )

            download_url = reverse('admin:shortlinks_shortlink_download_qr', args=[obj.pk])
            parts.append(
                f'<a class="button" href="{download_url}" '
                f'style="margin-right:8px">Завантажити SVG</a>'
            )

        generate_url = reverse('admin:shortlinks_shortlink_generate_qr', args=[obj.pk])
        btn_label = 'Перегенерувати QR' if obj.qr_svg else 'Згенерувати QR'
        parts.append(f'<a class="button" href="{generate_url}">{btn_label}</a>')

        return format_html(''.join(parts))

    def get_urls(self):
        custom = [
            path(
                '<int:pk>/generate-qr/',
                self.admin_site.admin_view(self.generate_qr_view),
                name='shortlinks_shortlink_generate_qr',
            ),
            path(
                '<int:pk>/download-qr/',
                self.admin_site.admin_view(self.download_qr_view),
                name='shortlinks_shortlink_download_qr',
            ),
        ]
        return custom + super().get_urls()

    def generate_qr_view(self, request, pk):
        obj = self.get_object(request, pk)
        obj.generate_qr()
        self.message_user(request, f'QR-код для /go/{obj.slug} згенеровано.')
        return HttpResponseRedirect(
            reverse('admin:shortlinks_shortlink_change', args=[pk])
        )

    def download_qr_view(self, request, pk):
        obj = self.get_object(request, pk)
        if not obj.qr_svg:
            self.message_user(request, 'QR-код ще не згенеровано.', level='error')
            return HttpResponseRedirect(
                reverse('admin:shortlinks_shortlink_change', args=[pk])
            )
        response = HttpResponse(obj.qr_svg, content_type='image/svg+xml')
        response['Content-Disposition'] = f'attachment; filename="qr_{obj.slug}.svg"'
        return response

    @admin.action(description='Згенерувати QR-коди для обраних')
    def generate_qr_bulk(self, request, queryset):
        count = 0
        for obj in queryset.filter(is_active=True):
            obj.generate_qr()
            count += 1
        self.message_user(request, f'Згенеровано QR-кодів: {count}.')
