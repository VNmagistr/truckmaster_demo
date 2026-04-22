from django.db import models


class ShortLink(models.Model):
    slug = models.SlugField(
        unique=True,
        max_length=64,
        help_text="Частина URL після /go/ (напр. 'maps', 'bot', 'review').",
    )
    target_url = models.URLField(
        max_length=2048,
        help_text="Куди редіректить (напр. посилання на Google Maps, Telegram-бот).",
    )
    label = models.CharField(
        max_length=200,
        blank=True,
        help_text="Опис для адмінки (не показується користувачу).",
    )
    is_active = models.BooleanField(default=True)
    hits = models.PositiveIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['slug']
        verbose_name = 'Коротке посилання'
        verbose_name_plural = 'Короткі посилання'

    def __str__(self):
        return f'/go/{self.slug} → {self.target_url}'
