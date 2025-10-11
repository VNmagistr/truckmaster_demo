# orders/urls.py

from rest_framework.routers import DefaultRouter
from .views import (
    ServiceOrderViewSet,
    ServiceWorkViewSet,
    UsedPartViewSet,
    EmployeeViewSet,
    WorkCategoryViewSet,
    RepairPhotoViewSet,
    RecentOrdersViewSet
)

router = DefaultRouter()
router.register(r'orders', ServiceOrderViewSet, basename='serviceorder')
router.register(r'service-works', ServiceWorkViewSet)
router.register(r'used-parts', UsedPartViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'work-categories', WorkCategoryViewSet)
router.register(r'repair-photos', RepairPhotoViewSet)
router.register(r'recent-orders', RecentOrdersViewSet, basename='recent-orders')

urlpatterns = router.urls