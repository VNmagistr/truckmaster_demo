<<<<<<< HEAD
=======
# inventory/urls.py

>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductCategoryViewSet,
    ProductSubcategoryViewSet,
    WarehouseViewSet,
<<<<<<< HEAD
    PartViewSet,
    StockViewSet,
    StockMovementViewSet,
=======
    PartCategoryViewSet,
    PartViewSet,
    StockViewSet,
    StockMovementViewSet,
    UsedPartViewSet,
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
)

router = DefaultRouter()
router.register(r'categories', ProductCategoryViewSet, basename='category')
router.register(r'subcategories', ProductSubcategoryViewSet, basename='subcategory')
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
<<<<<<< HEAD
=======
router.register(r'part-categories', PartCategoryViewSet, basename='part-category')
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
router.register(r'products', PartViewSet, basename='product')
router.register(r'parts', PartViewSet, basename='part')  # Для сумісності
router.register(r'stock', StockViewSet, basename='stock')
router.register(r'movements', StockMovementViewSet, basename='movement')
<<<<<<< HEAD

urlpatterns = [
    path('', include(router.urls)),
]
=======
router.register(r'used-parts', UsedPartViewSet, basename='used-part')

urlpatterns = [
    path('', include(router.urls)),
]
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
