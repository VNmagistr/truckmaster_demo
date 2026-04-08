from rest_framework.permissions import BasePermission, SAFE_METHODS


def _role(user):
    """Повертає роль користувача або None."""
    try:
        return user.profile.role
    except AttributeError:
        return None


class IsAdminRole(BasePermission):
    """Тільки адміністратор CRM."""
    message = "Доступно лише адміністратору."

    def has_permission(self, request, view):
        return request.user.is_superuser or _role(request.user) == 'admin'


class IsManagerOrAbove(BasePermission):
    """Менеджер або адміністратор."""
    message = "Недостатньо прав. Потрібна роль менеджера або вище."

    def has_permission(self, request, view):
        return request.user.is_superuser or _role(request.user) in ('admin', 'manager')


class CanManageStock(BasePermission):
    """Адмін, менеджер або комірник."""
    message = "Управління складом доступне лише адміністратору, менеджеру або комірнику."

    def has_permission(self, request, view):
        return request.user.is_superuser or _role(request.user) in ('admin', 'manager', 'storekeeper')


class CanAccessInvoices(BasePermission):
    """Адмін, менеджер або бухгалтер. Механіки та комірники не мають доступу."""
    message = "Доступ до рахунків обмежено. Зверніться до менеджера."

    def has_permission(self, request, view):
        return request.user.is_superuser or _role(request.user) in ('admin', 'manager', 'accountant')
