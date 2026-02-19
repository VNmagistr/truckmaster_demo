from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Category, SubCategory, Warehouse, StockItem, StockMovement
from .serializers import (
    ProductSerializer,
    ProductListSerializer,
    CategorySerializer,
    SubCategorySerializer,
    WarehouseSerializer,
    StockItemSerializer,
    StockMovementSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet для категорій товарів"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'slug']
    ordering_fields = ['sort_order', 'name']


class SubCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet для підкатегорій товарів"""
    queryset = SubCategory.objects.select_related('category').all()
    serializer_class = SubCategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'slug']
    ordering_fields = ['name']


class WarehouseViewSet(viewsets.ModelViewSet):
    """ViewSet для складів"""
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'address']


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet для товарів/запчастин
    Підтримує всі CRUD операції
    """
    queryset = Product.objects.select_related('subcategory', 'subcategory__category').all()

    # Фільтри та пошук
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Поля фільтрації (точний збіг)
    filterset_fields = ['subcategory', 'subcategory__category', 'is_active', 'brand']

    # Поля пошуку (частковий збіг)
    search_fields = ['name', 'sku_code', 'brand', 'notes']

    ordering_fields = ['name', 'current_stock', 'selling_price', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Використовуємо скорочений серіалізатор для списків"""
        if self.action == 'list':
            return ProductListSerializer
        return ProductSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Обробка фільтру "Низький залишок"
        low_stock = self.request.query_params.get('low_stock', None)
        if low_stock == 'true':
            from django.db.models import F
            queryset = queryset.filter(current_stock__lte=F('min_stock_level'))

        # Фільтр по статусу видалення
        show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'
        if not show_deleted:
            queryset = queryset.filter(marked_for_deletion=False)

        return queryset

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Фізичне видалення заборонено. Використовуйте позначення на видалення."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(detail=True, methods=['post'])
    def mark_for_deletion(self, request, pk=None):
        """Позначити товар на видалення (м'яке видалення)."""
        product = self.get_object()
        product.marked_for_deletion = True
        product.marked_for_deletion_by = request.user
        product.marked_for_deletion_at = timezone.now()
        product.deletion_reason = request.data.get('reason', '')
        product.save()
        return Response({'status': 'success'})

    @action(detail=True, methods=['post'])
    def unmark_for_deletion(self, request, pk=None):
        """Зняти позначку на видалення."""
        product = self.get_object()
        product.marked_for_deletion = False
        product.deletion_reason = ''
        product.marked_for_deletion_by = None
        product.marked_for_deletion_at = None
        product.save()
        return Response({'status': 'success'})


class StockItemViewSet(viewsets.ModelViewSet):
    """ViewSet для залишків на складах"""
    queryset = StockItem.objects.select_related('warehouse', 'product').all()
    serializer_class = StockItemSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['warehouse', 'product']
    search_fields = ['product__name', 'product__sku_code', 'location']
    ordering_fields = ['quantity', 'updated_at']


class StockMovementViewSet(viewsets.ModelViewSet):
    """ViewSet для руху товарів"""
    queryset = StockMovement.objects.select_related(
        'product', 'warehouse_from', 'warehouse_to', 'created_by'
    ).all()
    serializer_class = StockMovementSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['movement_type', 'warehouse_from', 'warehouse_to', 'product']
    search_fields = ['product__name', 'invoice_number', 'supplier', 'notes']
    ordering_fields = ['created_at', 'quantity']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        """Автоматично встановлюємо користувача, який створив рух"""
        serializer.save(created_by=self.request.user)