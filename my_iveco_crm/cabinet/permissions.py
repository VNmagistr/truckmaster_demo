from rest_framework.permissions import BasePermission


class IsClientUser(BasePermission):
    """
    Дозволяє доступ лише аутентифікованим користувачам,
    які мають прив'язаний профіль клієнта (Client.user).
    """
    message = "Доступ дозволено лише клієнтам."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'client_profile')
        )


class ClientHasCabinetAccess(BasePermission):
    """
    Перевіряє, що для клієнта увімкнено функцію 'cabinet'.
    Використовується разом з IsClientUser.
    """
    message = "Доступ до особистого кабінету вимкнено для вашого акаунту."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        try:
            return request.user.client_profile.features.cabinet
        except Exception:
            return False


class ClientEmailVerified(BasePermission):
    """
    Перевіряє, що клієнт підтвердив свою email адресу.
    Використовується для захисту ендпоінтів, недоступних до верифікації.
    """
    message = "Будь ласка, підтвердіть вашу email адресу для доступу до цієї функції."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        try:
            return request.user.client_profile.email_verified
        except Exception:
            return False
