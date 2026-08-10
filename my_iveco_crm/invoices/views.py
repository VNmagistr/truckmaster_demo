import logging
from django.db import transaction
from django.db.models.functions import Greatest
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from users.permissions import CanAccessInvoices
from rest_framework.response import Response

from .models import Invoice, InvoiceItem, DriverPickupLog, _next_invoice_number, _next_driver_tab_number
from .serializers import InvoiceSerializer, InvoiceListSerializer, InvoiceItemSerializer, DriverPickupLogSerializer

logger = logging.getLogger(__name__)


class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, CanAccessInvoices]
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
        if invoice_type := params.get('invoice_type'):
            qs = qs.filter(invoice_type=invoice_type)
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

        with transaction.atomic():
            if new_status == 'paid':
                stock_error = self._check_and_deduct_stock(invoice)
                if stock_error:
                    return Response({'detail': stock_error}, status=status.HTTP_400_BAD_REQUEST)
            invoice.status = new_status
            invoice.save(update_fields=['status', 'updated_at'])

        return Response(InvoiceSerializer(invoice, context={'request': request}).data)

    def _check_and_deduct_stock(self, invoice):
        """Перевіряє наявність і списує зі складу атомарно з select_for_update + F()."""
        from decimal import Decimal
        from django.db.models import F
        from inventory.models import Product, StockMovement

        items = invoice.items.filter(product__isnull=False).select_related('product')
        product_ids = [item.product_id for item in items]
        locked_products = {
            p.pk: p
            for p in Product.objects.select_for_update().filter(pk__in=product_ids)
        }

        insufficient = []
        for item in items:
            product = locked_products[item.product_id]
            stock = product.current_stock or Decimal('0')
            if stock < item.quantity:
                insufficient.append(
                    f'{product.name}: є {stock}, потрібно {item.quantity}'
                )
        if insufficient:
            return 'Недостатньо товарів на складі: ' + '; '.join(insufficient)

        for item in items:
            Product.objects.filter(pk=item.product_id).update(
                current_stock=Greatest(F('current_stock') - item.quantity, Decimal('0')),
            )
            StockMovement.objects.create(
                product_id=item.product_id,
                movement_type='out',
                quantity=item.quantity,
                invoice_number=invoice.number,
                notes=f'Продаж за рахунком {invoice.number}',
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

    @action(detail=True, methods=['post'])
    def send_ttn(self, request, pk=None):
        """Надіслати ТТН Нової Пошти клієнту через Telegram та/або WhatsApp."""
        invoice = self.get_object()

        if not invoice.nova_poshta_declaration:
            return Response(
                {'detail': 'У рахунку не вказано номер декларації Нової Пошти.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client = invoice.client
        if not client:
            return Response(
                {'detail': 'Рахунок не прив\'язаний до клієнта.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tracking_url = f'https://tracking.novaposhta.ua/#/uk/parcel/{invoice.nova_poshta_declaration}'
        text = (
            f'📦 Ваше замовлення відправлено!\n\n'
            f'Рахунок: {invoice.number}\n'
            f'ТТН Нової Пошти: {invoice.nova_poshta_declaration}\n\n'
            f'Відстежити посилку:\n{tracking_url}'
        )

        sent_to = []
        errors = []

        # Telegram
        try:
            features = client.features
        except Exception:
            features = None

        tg_allowed = (
            client.telegram_chat_id
            and (features is None or features.notifications_telegram)
        )
        if tg_allowed:
            from invoices.tasks import send_ttn_telegram
            send_ttn_telegram.delay(client.telegram_chat_id, text, invoice.number)
            sent_to.append('telegram')

        # WhatsApp
        wa_allowed = (
            client.phone
            and (features is None or features.notifications_whatsapp)
        )
        if wa_allowed:
            try:
                from my_iveco_crm.whatsapp import send_whatsapp_text
                send_whatsapp_text(client.phone, text)
                sent_to.append('whatsapp')
            except Exception as e:
                logger.error(f'TTN send WhatsApp error (invoice {invoice.number}): {e}')
                errors.append('whatsapp')

        if not sent_to and not errors:
            return Response(
                {'detail': 'Клієнт не має підключених каналів сповіщень (Telegram/WhatsApp).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            'sent_to': sent_to,
            'errors': errors,
            'declaration': invoice.nova_poshta_declaration,
        })


class InvoiceItemViewSet(viewsets.ModelViewSet):
    serializer_class   = InvoiceItemSerializer
    permission_classes = [IsAuthenticated, CanAccessInvoices]

    def get_queryset(self):
        qs = InvoiceItem.objects.select_related('product', 'invoice')
        if invoice_id := self.request.query_params.get('invoice'):
            qs = qs.filter(invoice_id=invoice_id)
        return qs.order_by('id')

    def perform_create(self, serializer):
        # invoice передається у полі invoice через серіалізатор
        serializer.save()


class DriverPickupLogViewSet(viewsets.ModelViewSet):
    serializer_class   = DriverPickupLogSerializer
    permission_classes = [IsAuthenticated, CanAccessInvoices]

    def get_queryset(self):
        qs = DriverPickupLog.objects.select_related('client', 'truck', 'product', 'invoice')
        params = self.request.query_params
        if client := params.get('client'):
            qs = qs.filter(client_id=client)
        if truck := params.get('truck'):
            qs = qs.filter(truck_id=truck)
        if params.get('uninvoiced') == '1':
            qs = qs.filter(invoice__isnull=True)
        if date_from := params.get('date_from'):
            qs = qs.filter(date__gte=date_from)
        if date_to := params.get('date_to'):
            qs = qs.filter(date__lte=date_to)
        return qs.order_by('-date', '-created_at')

    @action(detail=False, methods=['post'], url_path='generate-invoice')
    def generate_invoice(self, request):
        client_id = request.data.get('client')
        truck_id  = request.data.get('truck') or None

        if not client_id:
            return Response(
                {'detail': 'Оберіть клієнта.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pickups_qs = DriverPickupLog.objects.filter(
            client_id=client_id, invoice__isnull=True,
        ).select_related('product')
        if truck_id:
            pickups_qs = pickups_qs.filter(truck_id=truck_id)
        pickups = list(pickups_qs)

        if not pickups:
            return Response(
                {'detail': 'Немає незарахованих видач для цього клієнта.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            invoice = Invoice.objects.create(
                number=_next_driver_tab_number(),
                client_id=client_id,
                truck_id=truck_id,
                invoice_type='driver_tab',
            )
            for pickup in pickups:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=pickup.product,
                    description=f"{pickup.date.strftime('%d.%m.%Y')} — {pickup.description}",
                    quantity=pickup.quantity,
                    unit_price=pickup.unit_price,
                )
            DriverPickupLog.objects.filter(pk__in=[p.pk for p in pickups]).update(invoice=invoice)
            invoice.recalc_total()

        return Response(
            InvoiceSerializer(invoice, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def track_nova_poshta(request, number):
    """Відстеження посилки Нової Пошти за номером декларації."""
    from django.core.cache import cache
    from bot.nova_poshta import _np_api_track

    cache_key = f'np_track_{number}'
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    data = _np_api_track(number)
    if 'error' in data:
        return Response(
            {'detail': data['error']},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    cache.set(cache_key, data, timeout=120)
    return Response(data)
