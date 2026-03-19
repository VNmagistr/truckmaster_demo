# core/models.py

from django.db import models


class Module(models.Model):
    name = models.CharField(
        max_length=100, unique=True,
        verbose_name='Назва (код)',
    )
    label = models.CharField(max_length=200, verbose_name='Заголовок')
    description = models.TextField(blank=True, verbose_name='Опис')
    is_enabled = models.BooleanField(default=True, verbose_name='Увімкнено')
    is_core = models.BooleanField(
        default=False, verbose_name='Базовий модуль',
        help_text='Базові модулі не можна вимкнути — від них залежить вся система.',
    )
    url_prefixes = models.JSONField(
        default=list, verbose_name='URL префікси',
        help_text='Список URL-префіксів, які блокуються при вимкненні модуля.',
    )
    dependencies = models.JSONField(
        default=list, verbose_name='Залежності',
        help_text='Коди модулів, які мають бути увімкнені для роботи цього.',
    )
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Порядок')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Оновлено')

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Модуль'
        verbose_name_plural = 'Модулі'

    def __str__(self):
        return f'{self.label} ({self.name})'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from core.registry import clear_module_cache
        clear_module_cache(self.name)
