# core/admin.py

from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils.html import format_html

from .models import Module


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    change_list_template = 'admin/core/module/change_list.html'

    list_display = ['label', 'name', 'toggle_switch', 'is_core', 'deps_display', 'updated_at']
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
    def toggle_switch(self, obj):
        if obj.is_core:
            return format_html(
                '<label class="module-toggle module-toggle--core" title="Базовий модуль — не можна вимкнути">'
                '<input type="checkbox" class="module-toggle__input" checked disabled>'
                '<span class="module-toggle__track"><span class="module-toggle__thumb"></span></span>'
                '<span class="module-toggle__label">Базовий</span>'
                '</label>',
            )

        checked = 'checked' if obj.is_enabled else ''
        caption = 'Увімкнено' if obj.is_enabled else 'Вимкнено'

        return format_html(
            '<label class="module-toggle" data-pk="{}" title="{}">'
            '<input type="checkbox" class="module-toggle__input" {}>'
            '<span class="module-toggle__track"><span class="module-toggle__thumb"></span></span>'
            '<span class="module-toggle__label">{}</span>'
            '</label>',
            obj.pk, caption, checked, caption,
        )

    @admin.display(description='Залежності')
    def deps_display(self, obj):
        if not obj.dependencies:
            return '—'
        return ', '.join(obj.dependencies)

    # ── AJAX toggle endpoint ─────────────────────────────────

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pk>/toggle/',
                self.admin_site.admin_view(self.toggle_view),
                name='core_module_toggle',
            ),
        ]
        return custom_urls + urls

    def toggle_view(self, request, pk):
        if request.method != 'POST':
            return JsonResponse({'error': 'Method not allowed'}, status=405)

        module = get_object_or_404(Module, pk=pk)

        if module.is_core:
            return JsonResponse(
                {'error': f'Модуль "{module.label}" є базовим — не можна вимкнути.'},
                status=400,
            )

        # Якщо вимикаємо — перевіряємо чи є активні залежники
        if module.is_enabled:
            dependents = Module.objects.filter(is_enabled=True).exclude(pk=pk)
            blocking = [m.label for m in dependents if module.name in (m.dependencies or [])]
            if blocking:
                return JsonResponse(
                    {
                        'error': (
                            f'Не можна вимкнути "{module.label}" — '
                            f'від нього залежать: {", ".join(blocking)}.'
                        )
                    },
                    status=400,
                )

        module.is_enabled = not module.is_enabled
        module.save()

        return JsonResponse({
            'is_enabled': module.is_enabled,
            'label': module.label,
        })

    def save_model(self, request, obj, form, change):
        if change and not obj.is_enabled and 'is_enabled' in form.changed_data:
            dependents = Module.objects.filter(is_enabled=True).exclude(pk=obj.pk)
            blocking = [m.label for m in dependents if obj.name in (m.dependencies or [])]
            if blocking:
                from django.contrib import messages
                obj.is_enabled = True  # відкочуємо зміну
                super().save_model(request, obj, form, change)
                self.message_user(
                    request,
                    f'Не можна вимкнути "{obj.label}" — від нього залежать: {", ".join(blocking)}.',
                    level=messages.ERROR,
                )
                return
        super().save_model(request, obj, form, change)

    # ── Permissions ──────────────────────────────────────────

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
