from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductCategoryViewSet,
    ProductSubcategoryViewSet,
    WarehouseViewSet,
    PartViewSet,
    StockViewSet,
    StockMovementViewSet,
)

router = DefaultRouter()
router.register(r'categories', ProductCategoryViewSet, basename='category')
router.register(r'subcategories', ProductSubcategoryViewSet, basename='subcategory')
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
router.register(r'products', PartViewSet, basename='product')
router.register(r'parts', PartViewSet, basename='part')  # Для сумісності
router.register(r'stock', StockViewSet, basename='stock')
router.register(r'movements', StockMovementViewSet, basename='movement')

urlpatterns = [
    path('', include(router.urls)),
]
