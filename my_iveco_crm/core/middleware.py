# core/middleware.py

from django.http import JsonResponse

from core.registry import get_registry, is_module_enabled


class ModuleMiddleware:
    """
    Middleware, що перевіряє чи увімкнено модуль для кожного запиту.
    Якщо URL відповідає prefix вимкненого модуля — повертає 503.
    Базові (core) модулі завжди доступні.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        registry = get_registry()

        for name, info in registry.items():
            if info.get('is_core', False):
                continue

            for prefix in info.get('url_prefixes', []):
                if request.path.startswith(prefix):
                    if not is_module_enabled(name):
                        return JsonResponse(
                            {
                                'error': f'Модуль "{info["label"]}" вимкнено.',
                                'module': name,
                            },
                            status=503,
                        )

        return self.get_response(request)
