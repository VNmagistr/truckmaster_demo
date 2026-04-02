from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    SubCategoryViewSet,
    WarehouseViewSet,
    ProductViewSet,
    StockItemViewSet,
    StockMovementViewSet,
    UsedPartViewSet,
    OrderFolderViewSet,
    OrderItemViewSet,
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'subcategories', SubCategoryViewSet, basename='subcategory')
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'stock', StockItemViewSet, basename='stock')
router.register(r'movements', StockMovementViewSet, basename='movement')
router.register(r'used-parts', UsedPartViewSet, basename='used-parts')
router.register(r'order-folders', OrderFolderViewSet, basename='order-folder')
router.register(r'order-items', OrderItemViewSet, basename='order-item')

urlpatterns = [
    path('', include(router.urls)),
]