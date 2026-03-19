# core/registry.py
# Реєстр модулів системи. Заповнюється при старті через apps.py.ready() кожного app.

_REGISTRY: dict[str, dict] = {}


def register_module(info: dict) -> None:
    """Реєструє модуль у глобальному реєстрі."""
    _REGISTRY[info['name']] = info


def get_registry() -> dict:
    """Повертає весь реєстр модулів."""
    return _REGISTRY


def is_module_enabled(name: str) -> bool:
    """
    Перевіряє чи увімкнено модуль. Результат кешується на 60 секунд.
    Якщо модуль не знайдено в БД — вважається увімкненим.
    """
    from django.core.cache import cache

    cache_key = f'module_enabled:{name}'
    result = cache.get(cache_key)

    if result is None:
        try:
            from core.models import Module
            module = Module.objects.get(name=name)
            result = module.is_enabled
        except Exception:
            result = True  # за замовчуванням — увімкнено

        cache.set(cache_key, result, timeout=60)

    return result


def clear_module_cache(name: str) -> None:
    """Очищає кеш стану модуля після зміни."""
    from django.core.cache import cache
    cache.delete(f'module_enabled:{name}')
