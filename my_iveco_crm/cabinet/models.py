import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone


def _default_expiry():
    return timezone.now() + timedelta(hours=24)


class EmailVerification(models.Model):
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.CASCADE,
        related_name='email_verifications',
        verbose_name='Клієнт',
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    email = models.EmailField(verbose_name='Email')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_default_expiry)
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Email верифікація'
        verbose_name_plural = 'Email верифікації'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.client.name} — {self.email}"

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
