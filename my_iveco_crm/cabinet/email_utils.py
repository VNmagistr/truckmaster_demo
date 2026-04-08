from django.conf import settings
from django.core.mail import send_mail

from .models import EmailVerification


def send_verification_email(client, email):
    """Invalidates old tokens, creates a new one, and sends the verification email."""
    EmailVerification.objects.filter(client=client, is_used=False).update(is_used=True)

    verification = EmailVerification.objects.create(client=client, email=email)

    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://ital-truck.com.ua')
    verify_url = f"{frontend_url}/cabinet/verify-email?token={verification.token}"

    subject = "Підтвердження email — Італ Трак"
    message = (
        f"Вітаємо, {client.name}!\n\n"
        f"Для підтвердження вашої email адреси перейдіть за посиланням:\n\n"
        f"{verify_url}\n\n"
        f"Посилання дійсне протягом 24 годин.\n\n"
        f"З повагою,\nСервісний центр Італ Трак"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )

    return verification
