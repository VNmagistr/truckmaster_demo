import io

import qrcode
import qrcode.image.svg
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
    qr_svg = models.TextField(
        blank=True,
        default='',
        editable=False,
        verbose_name='QR-код (SVG)',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    BASE_URL = 'https://ital-truck.com.ua'

    class Meta:
        ordering = ['slug']
        verbose_name = 'QR-код'
        verbose_name_plural = 'QR-коди'

    def __str__(self):
        return f'/go/{self.slug} → {self.target_url}'

    @property
    def full_url(self):
        return f'{self.BASE_URL}/go/{self.slug}'

    def generate_qr(self):
        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
            image_factory=qrcode.image.svg.SvgPathImage,
        )
        qr.add_data(self.full_url)
        qr.make(fit=True)
        img = qr.make_image()
        buf = io.BytesIO()
        img.save(buf)
        self.qr_svg = buf.getvalue().decode('utf-8')
        self.save(update_fields=['qr_svg'])
