import logging
import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Invoice, InvoiceItem, _next_invoice_number
from .serializers import InvoiceSerializer, InvoiceListSerializer, InvoiceItemSerializer

logger = logging.getLogger(__name__)


class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    ordering           = ['-date', '-created_at']

    def get_queryset(self):
        qs = Invoice.objects.select_related(
            'client', 'truck'
        ).prefetch_related('items').order_by('-date', '-created_at')

        params = self.request.query_params
        if st := params.get('status'):
            qs = qs.filter(status=st)
        if client := params.get('client'):
            qs = qs.filter(client_id=client)
        if date_from := params.get('date_from'):
            qs = qs.filter(date__gte=date_from)
        if date_to := params.get('date_to'):
            qs = qs.filter(date__lte=date_to)
        if search := params.get('search'):
            from django.db.models import Q
            qs = qs.filter(
                Q(number__icontains=search) |
                Q(client__name__icontains=search) |
                Q(truck__license_plate__icontains=search)
            )
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        return InvoiceSerializer

    def perform_create(self, serializer):
        serializer.save(number=_next_invoice_number())

    def _change_status(self, request, new_status):
        invoice = self.get_object()
        if invoice.status == new_status:
            return Response(
                {'detail': 'Статус вже встановлено.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if invoice.status == 'cancelled':
            return Response(
                {'detail': 'Скасований рахунок не можна змінити.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if new_status == 'paid':
            stock_error = self._check_stock(invoice)
            if stock_error:
                return Response({'detail': stock_error}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            invoice.status = new_status
            invoice.save(update_fields=['status', 'updated_at'])
            if new_status == 'paid':
                self._deduct_stock(invoice)

        return Response(InvoiceSerializer(invoice, context={'request': request}).data)

    def _check_stock(self, invoice):
        """Повертає повідомлення про помилку якщо якогось товару недостатньо, інакше None."""
        from inventory.models import Product
        items = invoice.items.select_related('product').all()
        insufficient = []
        for item in items:
            if not item.product_id:
                continue
            product = Product.objects.get(pk=item.product_id)
            if (product.current_stock or 0) < item.quantity:
                insufficient.append(
                    f'{product.name}: є {product.current_stock or 0}, потрібно {item.quantity}'
                )
        if insufficient:
            return 'Недостатньо товарів на складі: ' + '; '.join(insufficient)
        return None

    def _deduct_stock(self, invoice):
        from inventory.models import StockMovement, Product
        for item in invoice.items.select_related('product').all():
            if not item.product_id:
                continue
            StockMovement.objects.create(
                product=item.product,
                movement_type='out',
                quantity=item.quantity,
                invoice_number=invoice.number,
                notes=f'Продаж за рахунком {invoice.number}',
            )
            from decimal import Decimal
            Product.objects.filter(pk=item.product_id).update(
                current_stock=max(
                    Decimal('0'),
                    (item.product.current_stock or Decimal('0')) - item.quantity,
                )
            )

    @action(detail=True, methods=['post'])
    def mark_sent(self, request, pk=None):
        return self._change_status(request, 'sent')

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        return self._change_status(request, 'paid')

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        return self._change_status(request, 'cancelled')


class InvoiceItemViewSet(viewsets.ModelViewSet):
    serializer_class   = InvoiceItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = InvoiceItem.objects.select_related('product', 'invoice')
        if invoice_id := self.request.query_params.get('invoice'):
            qs = qs.filter(invoice_id=invoice_id)
        return qs.order_by('id')

    def perform_create(self, serializer):
        # invoice передається у полі invoice через серіалізатор
        serializer.save()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def track_nova_poshta(request, number):
    """Відстеження посилки Нової Пошти за номером декларації."""
    api_key = getattr(settings, 'NP_API_KEY', '')
    if not api_key:
        return Response(
            {'detail': 'NP_API_KEY не налаштовано.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    payload = {
        'apiKey': api_key,
        'modelName': 'TrackingDocument',
        'calledMethod': 'getStatusDocuments',
        'methodProperties': {
            'Documents': [{'DocumentNumber': number}],
        },
    }

    try:
        resp = requests.post(
            'https://api.novaposhta.ua/v2.0/json/',
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error(f'Nova Poshta API error: {e}')
        return Response(
            {'detail': 'Помилка зв\'язку з API Нової Пошти.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if not data.get('success'):
        errors = data.get('errors', [])
        return Response(
            {'detail': errors[0] if errors else 'Помилка API Нової Пошти.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    docs = data.get('data', [])
    if not docs:
        return Response(
            {'detail': 'Декларацію не знайдено.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(docs[0])
