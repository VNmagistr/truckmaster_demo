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
