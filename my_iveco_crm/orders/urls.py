# orders/urls.py

from django.urls import path # <-- Додайте імпорт path
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceOrderViewSet,
    ServiceWorkViewSet,
    UsedPartViewSet,
    EmployeeViewSet,
    WorkCategoryViewSet,
    RepairPhotoViewSet,
    OrderStatsByStatusView # <-- Імпортуємо новий view
)

router = DefaultRouter()
router.register(r'orders', ServiceOrderViewSet, basename='serviceorder')
router.register(r'service-works', ServiceWorkViewSet)
router.register(r'used-parts', UsedPartViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'work-categories', WorkCategoryViewSet)
router.register(r'repair-photos', RepairPhotoViewSet)

# Додаємо маршрут для статистики окремо від роутера
urlpatterns = router.urls + [
    path('order-stats-by-status/', OrderStatsByStatusView.as_view(), name='order-stats-by-status'),
]