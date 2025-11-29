# inventory/views.py

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, F

from .models import (
    ProductCategory,
    ProductSubcategory,
    Warehouse,
    Part,
    Stock,
    StockMovement,
    PartCategory,
    UsedPart,
)
from .serializers import (
    ProductCategorySerializer,
    ProductSubcategorySerializer,
    WarehouseSerializer,
    PartSerializer,
    PartListSerializer,
    StockSerializer,
    StockMovementSerializer,
    PartCategorySerializer,
    UsedPartSerializer,
)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    """API для категорій товарів"""
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['category_type', 'is_active']
    search_fields = ['name']
    ordering = ['sort_order', 'name']


class ProductSubcategoryViewSet(viewsets.ModelViewSet):
    """API для підкатегорій товарів"""
    queryset = ProductSubcategory.objects.select_related('category').all()
    serializer_class = ProductSubcategorySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name']
    ordering = ['category', 'sort_order', 'name']


class WarehouseViewSet(viewsets.ModelViewSet):
    """API для складів"""
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active', 'is_default']
    ordering = ['sort_order', 'name']
    
    @action(detail=True, methods=['get'])
    def stock_summary(self, request, pk=None):
        """Підсумок по складу"""
        warehouse = self.get_object()
        stock_items = Stock.objects.filter(warehouse=warehouse)
        
        total_items = stock_items.count()
        total_quantity = stock_items.aggregate(total=Sum('quantity'))['total'] or 0
        total_value = stock_items.aggregate(
            total=Sum(F('quantity') * F('product__selling_price'))
        )['total'] or 0
        low_stock_count = sum(1 for s in stock_items if s.is_low_stock)
        
        return Response({
            'warehouse': WarehouseSerializer(warehouse).data,
            'total_items': total_items,
            'total_quantity': total_quantity,
            'total_value': total_value,
            'low_stock_count': low_stock_count,
        })


class PartCategoryViewSet(viewsets.ModelViewSet):
    """API для старих категорій запчастин (сумісність)"""
    queryset = PartCategory.objects.all()
    serializer_class = PartCategorySerializer
    permission_classes = [IsAuthenticated]


class PartViewSet(viewsets.ModelViewSet):
    """API для товарів/запчастин"""
    queryset = Part.objects.select_related('category', 'subcategory__category').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subcategory', 'subcategory__category', 'brand', 'is_active']
    search_fields = ['name', 'sku_code', 'brand', 'description']
    ordering_fields = ['name', 'sku_code', 'selling_price', 'current_stock', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PartListSerializer
        return PartSerializer
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Товари з низьким залишком"""
        products = self.queryset.filter(
            current_stock__lte=F('min_stock_level'),
            is_active=True
        )
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def oils(self, request):
        """Тільки оливи"""
        products = self.queryset.filter(
            subcategory__category__category_type='oil',
            is_active=True
        )
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def filters_list(self, request):
        """Тільки фільтри"""
        products = self.queryset.filter(
            subcategory__category__category_type='filter',
            is_active=True
        )
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class StockViewSet(viewsets.ModelViewSet):
    """API для залишків на складі"""
    queryset = Stock.objects.select_related(
        'warehouse', 
        'product', 
        'product__subcategory',
        'product__subcategory__category'
    ).all()
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['warehouse', 'product']
    search_fields = ['product__name', 'product__sku_code', 'location']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фільтр по низькому залишку
        low_stock = self.request.query_params.get('low_stock')
        if low_stock == 'true':
            # Фільтруємо в Python, бо is_low_stock - це property
            ids = [s.id for s in queryset if s.is_low_stock]
            queryset = queryset.filter(id__in=ids)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def by_product(self, request):
        """Залишки по всіх складах для товару"""
        product_id = request.query_params.get('product_id')
        if not product_id:
            return Response(
                {'error': 'product_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stock_items = self.queryset.filter(product_id=product_id)
        serializer = self.get_serializer(stock_items, many=True)
        return Response(serializer.data)


class StockMovementViewSet(viewsets.ModelViewSet):
    """API для руху товарів"""
    queryset = StockMovement.objects.select_related(
        'product',
        'warehouse_from',
        'warehouse_to',
        'service_order',
        'created_by'
    ).all()
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['movement_type', 'product', 'warehouse_from', 'warehouse_to']
    search_fields = ['product__name', 'invoice_number', 'supplier', 'notes']
    ordering_fields = ['created_at', 'quantity']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_product(self, request):
        """Історія руху для товару"""
        product_id = request.query_params.get('product_id')
        if not product_id:
            return Response(
                {'error': 'product_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        movements = self.queryset.filter(product_id=product_id)
        serializer = self.get_serializer(movements, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Останні 50 рухів"""
        movements = self.queryset[:50]
        serializer = self.get_serializer(movements, many=True)
        return Response(serializer.data)


class UsedPartViewSet(viewsets.ModelViewSet):
    """API для використаних запчастин"""
    queryset = UsedPart.objects.select_related('part', 'warehouse', 'service_work').all()
    serializer_class = UsedPartSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['service_work', 'part', 'warehouse']
