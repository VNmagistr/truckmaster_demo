import os
from rest_framework.permissions import BasePermission


class AlprApiKeyPermission(BasePermission):
    """
    Дозволяє доступ лише запитам з коректним API-ключем у заголовку X-ALPR-Key.
    Використовується для endpoint /api/alpr/event/ (ALPR-скрипт, не людина).
    """
    message = "Недійсний або відсутній ALPR API ключ."

    def has_permission(self, request, view):
        expected_key = os.environ.get('ALPR_API_KEY', '')
        if not expected_key:
            return False
        provided_key = request.headers.get('X-Alpr-Key', '')
        return provided_key == expected_key
