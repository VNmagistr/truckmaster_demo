import logging
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
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
        invoice.status = new_status
        invoice.save(update_fields=['status', 'updated_at'])
        if new_status == 'paid':
            self._deduct_stock(invoice)
        return Response(InvoiceSerializer(invoice, context={'request': request}).data)

    def _deduct_stock(self, invoice):
        try:
            from inventory.models import StockMovement, Product
            for item in invoice.items.select_related('product').all():
                if not item.product_id:
                    continue
                StockMovement.objects.create(
                    product=item.product,
                    movement_type='out',
                    quantity=float(item.quantity),
                    invoice_number=invoice.number,
                    notes=f'Продаж за рахунком {invoice.number}',
                )
                Product.objects.filter(pk=item.product_id).update(
                    current_stock=max(
                        0,
                        float(item.product.current_stock or 0) - float(item.quantity)
                    )
                )
        except Exception as e:
            logger.error(f'Помилка списання складу для рахунку {invoice.number}: {e}')

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
