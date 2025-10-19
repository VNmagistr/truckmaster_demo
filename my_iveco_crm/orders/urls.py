# orders/urls.py

from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceOrderViewSet,
    ServiceWorkViewSet,
    UsedPartViewSet,
    EmployeeViewSet,
    WorkCategoryViewSet,
    RepairPhotoViewSet,
    RecentOrdersViewSet,
    DashboardOrderStatsView,
    BotOrderStatusView # <-- Імпортуємо новий view
)

router = DefaultRouter()
router.register(r'orders', ServiceOrderViewSet, basename='serviceorder')
router.register(r'service-works', ServiceWorkViewSet)
router.register(r'used-parts', UsedPartViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'work-categories', WorkCategoryViewSet)
router.register(r'repair-photos', RepairPhotoViewSet)
router.register(r'recent-orders', RecentOrdersViewSet, basename='recent-orders')

# Додаємо маршрути для статистики та бота
urlpatterns = router.urls + [
    path('dashboard-order-stats/', DashboardOrderStatsView.as_view(), name='dashboard-order-stats'),
    # --- НОВИЙ МАРШРУТ ДЛЯ БОТА ---
    path('bot/order-status/<str:order_number>/', BotOrderStatusView.as_view(), name='bot-order-status'),
]