# inventory/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductCategoryViewSet,
    ProductSubcategoryViewSet,
    WarehouseViewSet,
    PartCategoryViewSet,
    PartViewSet,
    StockViewSet,
    StockMovementViewSet,
    UsedPartViewSet,
)

router = DefaultRouter()
router.register(r'categories', ProductCategoryViewSet, basename='category')
router.register(r'subcategories', ProductSubcategoryViewSet, basename='subcategory')
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
router.register(r'part-categories', PartCategoryViewSet, basename='part-category')
router.register(r'products', PartViewSet, basename='product')
router.register(r'parts', PartViewSet, basename='part')  # Для сумісності
router.register(r'stock', StockViewSet, basename='stock')
router.register(r'movements', StockMovementViewSet, basename='movement')
router.register(r'used-parts', UsedPartViewSet, basename='used-part')

urlpatterns = [
    path('', include(router.urls)),
]