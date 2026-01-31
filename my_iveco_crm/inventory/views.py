from rest_framework import viewsets, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Category, SubCategory, StockItem, StockMovement
from .serializers import (
    ProductSerializer, CategorySerializer, SubCategorySerializer,
    StockItemSerializer, StockMovementSerializer
)

class IsAuthenticated(permissions.IsAuthenticated):
    pass

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [IsAuthenticated]

class ProductViewSet(viewsets.ModelViewSet):
    # 🔥 БУЛО: ReadOnlyModelViewSet -> СТАЛО: ModelViewSet
    # ModelViewSet дозволяє методи:
    # - GET (читання)
    # - POST (створення)
    # - PUT/PATCH (редагування)
    # - DELETE (видалення)
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    
    # Фільтри та пошук
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Поля фільтрації (точний збіг)
    filterset_fields = ['category', 'subcategory', 'is_active', 'brand']
    
    # Поля пошуку (частковий збіг, який ми використовуємо на фронті)
    search_fields = ['name', 'sku_code', 'brand', 'description']
    
    ordering_fields = ['name', 'current_stock', 'selling_price', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Обробка фільтру "Низький залишок"
        low_stock = self.request.query_params.get('low_stock', None)
        if low_stock == 'true':
            from django.db.models import F
            queryset = queryset.filter(current_stock__lte=F('min_stock_level'))
            
        return queryset

class StockItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Залишки на конкретних складах зазвичай змінюються через документи (Movements),
    тому тут залишаємо ReadOnly, або змінюємо на ModelViewSet, якщо треба правити вручну.
    """
    queryset = StockItem.objects.all()
    serializer_class = StockItemSerializer
    permission_classes = [IsAuthenticated]

class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Історія руху товарів — це журнал, його зазвичай не редагують.
    """
    queryset = StockMovement.objects.all().order_by('-created_at')
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]