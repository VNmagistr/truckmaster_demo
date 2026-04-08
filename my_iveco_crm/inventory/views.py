from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsAdminRole, IsManagerOrAbove, CanManageStock
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from decimal import Decimal, InvalidOperation
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Category, SubCategory, Warehouse, StockItem, StockMovement, UsedPart, OrderFolder, OrderItem
import uuid
from .serializers import (
    ProductSerializer,
    ProductListSerializer,
    CategorySerializer,
    SubCategorySerializer,
    WarehouseSerializer,
    StockItemSerializer,
    StockMovementSerializer,
    UsedPartSerializer,
    OrderFolderSerializer,
    OrderItemSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet для категорій товарів"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'slug']
    ordering_fields = ['sort_order', 'name']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated()]


class SubCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet для підкатегорій товарів"""
    queryset = SubCategory.objects.select_related('category').all()
    serializer_class = SubCategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'slug']
    ordering_fields = ['name']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated()]


class WarehouseViewSet(viewsets.ModelViewSet):
    """ViewSet для складів"""
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'address']

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAuthenticated(), IsAdminRole()]
        if self.action in ('create', 'update', 'partial_update'):
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated()]


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet для товарів/запчастин
    Підтримує всі CRUD операції
    """
    queryset = Product.objects.select_related('subcategory', 'subcategory__category').all()

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAuthenticated(), IsAdminRole()]
        if self.action in ('create', 'update', 'partial_update'):
            return [IsAuthenticated(), CanManageStock()]
        return [IsAuthenticated()]

    # Фільтри та пошук
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]

    # Поля фільтрації (точний збіг)
    filterset_fields = ['subcategory', 'subcategory__category', 'subcategory__category__category_type', 'is_active', 'brand']

    ordering_fields = ['name', 'current_stock', 'selling_price', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Використовуємо скорочений серіалізатор для списків"""
        if self.action == 'list':
            return ProductListSerializer
        return ProductSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Фільтр тільки оливи: за category_type АБО за назвою (для товарів без категорії)
        oil_only = self.request.query_params.get('oil_only', None)
        if oil_only == 'true':
            OIL_TYPES = {'oil', 'олива', 'масло', 'мастило'}
            queryset = queryset.filter(
                Q(subcategory__category__category_type__in=list(OIL_TYPES)) |
                Q(name__iregex=r'^олива') |
                Q(name__icontains='олива моторна') |
                Q(name__iregex=r'^масло\s+мотор')
            )

        # Фільтр тільки фільтри: за category_type АБО за назвою (для товарів без категорії)
        filter_only = self.request.query_params.get('filter_only', None)
        if filter_only == 'true':
            FILTER_TYPES = {'filter', 'фільтр', 'фільтри'}
            queryset = queryset.filter(
                Q(subcategory__category__category_type__in=list(FILTER_TYPES)) |
                Q(subcategory__category__name__icontains='фільтр') |
                Q(name__iregex=r'^фільтр') |
                Q(name__icontains='шайба пробки') |
                Q(name__icontains='прокладка фільтра')
            )

        # Обробка фільтру "Низький залишок"
        low_stock = self.request.query_params.get('low_stock', None)
        if low_stock == 'true':
            from django.db.models import F
            queryset = queryset.filter(current_stock__lte=F('min_stock_level'))

        # Фільтр по статусу видалення
        show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'
        if not show_deleted:
            queryset = queryset.filter(marked_for_deletion=False)

        # Пошук за штрих-кодом (точний збіг або через sku_code)
        barcode = self.request.query_params.get('barcode', '').strip()
        if barcode:
            queryset = queryset.filter(
                Q(barcode=barcode) | Q(sku_code__iexact=barcode)
            )
            return queryset

        # Пошук: по артикулу (будь-яка частина) АБО по назві
        q = self.request.query_params.get('search', '').strip()
        if q:
            queryset = queryset.filter(
                Q(sku_code__icontains=q) | Q(name__icontains=q)
            )

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

    def get_permissions(self):
        # Перегляд — всі; запис і спеціальні дії — тільки ті, хто управляє складом
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'transfer', 'receive_stock'):
            return [IsAuthenticated(), CanManageStock()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Автоматично встановлюємо користувача, який створив рух"""
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'])
    def transfer(self, request):
        """Переміщення товару між складами. Оновлює StockItem на обох складах."""
        try:
            product = Product.objects.get(id=request.data.get('product'))
            warehouse_from = Warehouse.objects.get(id=request.data.get('warehouse_from'))
            warehouse_to = Warehouse.objects.get(id=request.data.get('warehouse_to'))
            quantity = Decimal(str(request.data.get('quantity', 0)))
        except (Product.DoesNotExist, Warehouse.DoesNotExist):
            return Response({'error': 'Товар або склад не знайдено'}, status=status.HTTP_400_BAD_REQUEST)
        except (InvalidOperation, TypeError):
            return Response({'error': 'Невірна кількість'}, status=status.HTTP_400_BAD_REQUEST)

        if quantity <= 0:
            return Response({'error': 'Кількість має бути більше 0'}, status=status.HTTP_400_BAD_REQUEST)
        if warehouse_from.id == warehouse_to.id:
            return Response({'error': 'Склади мають бути різними'}, status=status.HTTP_400_BAD_REQUEST)

        source_item, _ = StockItem.objects.get_or_create(
            warehouse=warehouse_from, product=product, defaults={'quantity': 0}
        )
        if source_item.quantity < quantity:
            return Response(
                {'error': f'Недостатньо товару. На складі: {source_item.quantity} {product.unit}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            source_item.quantity -= quantity
            source_item.save()

            dest_item, _ = StockItem.objects.get_or_create(
                warehouse=warehouse_to, product=product, defaults={'quantity': 0}
            )
            dest_item.quantity += quantity
            dest_item.save()

            # Синхронізуємо Product.current_stock: total = sum по всіх StockItem
            from django.db.models import Sum
            total_qty = StockItem.objects.filter(product=product).aggregate(
                total=Sum('quantity')
            )['total'] or 0
            product.current_stock = total_qty
            product.save(update_fields=['current_stock'])

            movement = StockMovement.objects.create(
                movement_type='transfer',
                product=product,
                quantity=quantity,
                warehouse_from=warehouse_from,
                warehouse_to=warehouse_to,
                created_by=request.user,
                notes=request.data.get('notes', ''),
            )

        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def receive_stock(self, request):
        """Надходження товару на будь-який склад (оптовий або роздрібний)."""
        try:
            product = Product.objects.get(id=request.data.get('product'))
            warehouse = Warehouse.objects.get(id=request.data.get('warehouse'))
            quantity = Decimal(str(request.data.get('quantity', 0)))
        except (Product.DoesNotExist, Warehouse.DoesNotExist):
            return Response({'error': 'Товар або склад не знайдено'}, status=status.HTTP_400_BAD_REQUEST)
        except (InvalidOperation, TypeError):
            return Response({'error': 'Невірна кількість'}, status=status.HTTP_400_BAD_REQUEST)

        if quantity <= 0:
            return Response({'error': 'Кількість має бути більше 0'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            stock_item, _ = StockItem.objects.get_or_create(
                warehouse=warehouse, product=product, defaults={'quantity': 0}
            )
            stock_item.quantity += quantity
            stock_item.save()

            from django.db.models import Sum
            total_qty = StockItem.objects.filter(product=product).aggregate(
                total=Sum('quantity')
            )['total'] or 0
            product.current_stock = total_qty
            product.save(update_fields=['current_stock'])

            movement = StockMovement.objects.create(
                movement_type='in',
                product=product,
                quantity=quantity,
                warehouse_to=warehouse,
                created_by=request.user,
                supplier=request.data.get('supplier', ''),
                invoice_number=request.data.get('invoice_number', ''),
                purchase_price=request.data.get('purchase_price') or None,
                notes=request.data.get('notes', ''),
            )

        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)


class UsedPartViewSet(viewsets.ModelViewSet):
    """ViewSet для використаних запчастин."""
    serializer_class = UsedPartSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['service_work', 'service_order', 'part', 'warehouse']
    search_fields = ['part__name', 'part__sku_code']
    ordering_fields = ['part__name', 'quantity', 'unit_price']

    def get_queryset(self):
        return UsedPart.objects.select_related(
            'part', 'warehouse', 'service_work', 'service_order'
        ).all()


class OrderFolderViewSet(viewsets.ModelViewSet):
    """ViewSet для папок замовлення"""
    serializer_class = OrderFolderSerializer

    def get_queryset(self):
        show_archived = self.request.query_params.get('show_archived', 'false').lower() == 'true'
        qs = OrderFolder.objects.prefetch_related('items').all()
        if not show_archived:
            qs = qs.filter(is_archived=False)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        folder = self.get_object()
        folder.is_archived = True
        folder.archived_at = timezone.now()
        folder.save()
        return Response(self.get_serializer(folder).data)

    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        folder = self.get_object()
        folder.is_archived = False
        folder.archived_at = None
        folder.save()
        return Response(self.get_serializer(folder).data)

    @action(detail=True, methods=['post'])
    def mark_all_ordered(self, request, pk=None):
        folder = self.get_object()
        folder.items.all().update(
            is_ordered=True,
            ordered_at=timezone.now(),
            ordered_by=request.user
        )
        serializer = self.get_serializer(folder)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def unmark_all_ordered(self, request, pk=None):
        folder = self.get_object()
        folder.items.all().update(is_ordered=False, ordered_at=None, ordered_by=None)
        serializer = self.get_serializer(folder)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def receive_all(self, request, pk=None):
        """Масове оприбуткування всіх позицій з прив'язкою до товару.
        Body:
          warehouse_id: int (required)
        """
        folder = self.get_object()
        warehouse_id = request.data.get('warehouse_id')
        if not warehouse_id:
            return Response({'error': 'warehouse_id обов\'язковий'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            warehouse = Warehouse.objects.get(id=warehouse_id)
        except Warehouse.DoesNotExist:
            return Response({'error': 'Склад не знайдено'}, status=status.HTTP_400_BAD_REQUEST)

        items = folder.items.filter(
            is_ordered=True, is_received=False, linked_product__isnull=False
        ).select_related('linked_product')

        if not items.exists():
            return Response(
                {'error': 'Немає готових позицій (потрібно: замовлено + прив\'язано до товару)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        received_ids = []
        errors = []

        for item in items:
            try:
                quantity = Decimal(str(item.quantity or 1))
                product = item.linked_product

                with transaction.atomic():
                    stock_item, _ = StockItem.objects.get_or_create(
                        warehouse=warehouse, product=product, defaults={'quantity': 0}
                    )
                    stock_item.quantity += quantity
                    stock_item.save()

                    from django.db.models import Sum
                    total = StockItem.objects.filter(product=product).aggregate(
                        total=Sum('quantity')
                    )['total'] or 0
                    product.current_stock = total
                    product.save(update_fields=['current_stock'])

                    StockMovement.objects.create(
                        movement_type='in',
                        product=product,
                        quantity=quantity,
                        warehouse_to=warehouse,
                        created_by=request.user,
                        purchase_price=item.purchase_price or None,
                        notes=f'Масове надходження: {folder.name} / {item.name}',
                    )

                    item.is_received = True
                    item.received_at = timezone.now()
                    item.received_by = request.user
                    item.save()

                received_ids.append(item.id)
            except Exception as e:
                errors.append({'item': item.name, 'error': str(e)})

        return Response({
            'received': len(received_ids),
            'errors': errors,
            'folder': self.get_serializer(folder).data,
        })


class OrderItemViewSet(viewsets.ModelViewSet):
    """ViewSet для позицій замовлення"""
    queryset = OrderItem.objects.select_related('folder', 'ordered_by', 'received_by', 'linked_product').all()
    serializer_class = OrderItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['folder', 'is_ordered', 'is_received']

    @action(detail=True, methods=['post'])
    def toggle_ordered(self, request, pk=None):
        item = self.get_object()
        item.is_ordered = not item.is_ordered
        if item.is_ordered:
            item.ordered_at = timezone.now()
            item.ordered_by = request.user
        else:
            item.ordered_at = None
            item.ordered_by = None
        item.save()
        return Response(OrderItemSerializer(item).data)

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        """Оприбуткувати позицію на склад.
        Body:
          warehouse_id: int (required)
          quantity: decimal (optional, defaults to item.quantity)
          product_id: int (optional — existing product)
          sku_code: str (required if no product_id — for new product)
          product_name: str (optional, defaults to item.name)
          unit: str (optional)
        """
        item = self.get_object()
        if item.is_received:
            return Response({'error': 'Позицію вже оприбутковано'}, status=status.HTTP_400_BAD_REQUEST)

        warehouse_id = request.data.get('warehouse_id')
        if not warehouse_id:
            return Response({'error': 'warehouse_id обов\'язковий'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            warehouse = Warehouse.objects.get(id=warehouse_id)
        except Warehouse.DoesNotExist:
            return Response({'error': 'Склад не знайдено'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            raw_qty = request.data.get('quantity', item.quantity or 1)
            quantity = Decimal(str(raw_qty))
        except (InvalidOperation, TypeError):
            return Response({'error': 'Невірна кількість'}, status=status.HTTP_400_BAD_REQUEST)

        if quantity <= 0:
            return Response({'error': 'Кількість має бути більше 0'}, status=status.HTTP_400_BAD_REQUEST)

        product_id = request.data.get('product_id')

        with transaction.atomic():
            if product_id:
                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    return Response({'error': 'Товар не знайдено'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                sku_code = request.data.get('sku_code', '').strip()
                if not sku_code:
                    return Response({'error': 'sku_code обов\'язковий для нового товару'}, status=status.HTTP_400_BAD_REQUEST)
                product_name = request.data.get('product_name', item.name).strip()
                unit = request.data.get('unit', item.unit or 'pcs')
                product = Product.objects.create(
                    sku_code=sku_code,
                    name=product_name,
                    unit=unit,
                    current_stock=0,
                    notes=f'Створено з замовлення: {item.folder.name}',
                )

            # Add stock
            stock_item, _ = StockItem.objects.get_or_create(
                warehouse=warehouse, product=product, defaults={'quantity': 0}
            )
            stock_item.quantity += quantity
            stock_item.save()

            from django.db.models import Sum
            total = StockItem.objects.filter(product=product).aggregate(total=Sum('quantity'))['total'] or 0
            product.current_stock = total
            product.save(update_fields=['current_stock'])

            purchase_price = request.data.get('purchase_price') or None
            StockMovement.objects.create(
                movement_type='in',
                product=product,
                quantity=quantity,
                warehouse_to=warehouse,
                created_by=request.user,
                purchase_price=purchase_price,
                notes=f'Надходження з замовлення: {item.folder.name} / {item.name}',
            )

            item.is_received = True
            item.received_at = timezone.now()
            item.received_by = request.user
            item.linked_product = product
            item.save()

        return Response(OrderItemSerializer(item).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def search_products(self, request):
        """Пошук товарів для зіставлення з позицією замовлення."""
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response([])
        products = Product.objects.filter(
            Q(name__icontains=q) | Q(sku_code__icontains=q),
            marked_for_deletion=False,
        )[:20]
        from .serializers import ProductListSerializer
        return Response(ProductListSerializer(products, many=True).data)