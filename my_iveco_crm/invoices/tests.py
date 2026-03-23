import sys
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from clients.models import Client, IvecoBaseModel, Truck
from inventory.models import Product
from invoices.models import Invoice, InvoiceItem


class InvoiceMarkPaidTest(APITestCase):
    """Tests for mark_paid: stock validation and atomic status+deduction."""

    def setUp(self):
        self.user = User.objects.create_superuser('admin', password='pass')
        self.client.force_authenticate(user=self.user)

        self.buyer = Client.objects.create(name='Test Client')
        self.product = Product.objects.create(
            name='Oil Filter',
            sku_code='OIL-001',
            selling_price=Decimal('200.00'),
            current_stock=Decimal('10'),
        )

    def _make_invoice(self, qty):
        invoice = Invoice.objects.create(number='INV-001', client=self.buyer)
        InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            description=self.product.name,
            quantity=Decimal(str(qty)),
            unit_price=self.product.selling_price,
        )
        return invoice

    def _paid_url(self, pk):
        return f'/api/invoices/{pk}/mark_paid/'

    # ── Happy path ──────────────────────────────────────────────────────────

    def test_mark_paid_sufficient_stock_returns_200(self):
        invoice = self._make_invoice(qty=5)
        response = self.client.post(self._paid_url(invoice.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_mark_paid_deducts_stock(self):
        invoice = self._make_invoice(qty=3)
        self.client.post(self._paid_url(invoice.pk))
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, Decimal('7'))

    def test_mark_paid_sets_status_to_paid(self):
        invoice = self._make_invoice(qty=1)
        self.client.post(self._paid_url(invoice.pk))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'paid')

    # ── Insufficient stock ──────────────────────────────────────────────────

    def test_mark_paid_insufficient_stock_returns_400(self):
        invoice = self._make_invoice(qty=15)  # more than current_stock=10
        response = self.client.post(self._paid_url(invoice.pk))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_paid_insufficient_stock_keeps_draft_status(self):
        """Invoice must stay in draft when stock check fails."""
        invoice = self._make_invoice(qty=15)
        self.client.post(self._paid_url(invoice.pk))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'draft')

    def test_mark_paid_insufficient_stock_does_not_deduct(self):
        """Stock must not change when mark_paid is blocked."""
        invoice = self._make_invoice(qty=15)
        self.client.post(self._paid_url(invoice.pk))
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, Decimal('10'))

    def test_error_response_mentions_product_name(self):
        invoice = self._make_invoice(qty=15)
        response = self.client.post(self._paid_url(invoice.pk))
        self.assertIn('Oil Filter', response.data['detail'])

    # ── Atomicity ───────────────────────────────────────────────────────────

    def test_already_paid_returns_400(self):
        invoice = self._make_invoice(qty=1)
        invoice.status = 'paid'
        invoice.save(update_fields=['status'])
        response = self.client.post(self._paid_url(invoice.pk))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelled_invoice_cannot_be_paid(self):
        invoice = self._make_invoice(qty=1)
        invoice.status = 'cancelled'
        invoice.save(update_fields=['status'])
        response = self.client.post(self._paid_url(invoice.pk))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'cancelled')


class SendTtnTest(APITestCase):
    """Tests for send_ttn: TTN notification via Telegram and WhatsApp."""

    def setUp(self):
        self.user = User.objects.create_superuser('admin_ttn', password='pass')
        self.client.force_authenticate(user=self.user)

        self.buyer = Client.objects.create(name='TTN Client', phone='+380991234567')
        self.invoice = Invoice.objects.create(
            number='INV-TTN-001',
            client=self.buyer,
            nova_poshta_declaration='20450000000001',
        )

    def _url(self, pk=None):
        return f'/api/invoices/{pk or self.invoice.pk}/send_ttn/'

    # ── Validation guards ────────────────────────────────────────────────────

    def test_no_declaration_returns_400(self):
        inv = Invoice.objects.create(number='INV-TTN-002', client=self.buyer)
        response = self.client.post(self._url(inv.pk))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('декларації', response.data['detail'])

    def test_no_channels_returns_400(self):
        """Client has neither telegram_chat_id nor phone → 400."""
        buyer = Client.objects.create(name='No Channels Client')
        inv = Invoice.objects.create(
            number='INV-TTN-004',
            client=buyer,
            nova_poshta_declaration='20450000000003',
        )
        response = self.client.post(self._url(inv.pk))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Telegram ─────────────────────────────────────────────────────────────

    def _mock_telegram(self):
        """Return a sys.modules patch that stubs out python-telegram-bot."""
        mock_bot_instance = MagicMock()
        mock_bot_instance.send_message = AsyncMock()
        mock_telegram_module = MagicMock()
        mock_telegram_module.Bot.return_value = mock_bot_instance
        return patch.dict('sys.modules', {'telegram': mock_telegram_module}), mock_telegram_module

    def test_sends_via_telegram_when_configured(self):
        self.buyer.telegram_chat_id = 123456789
        self.buyer.save(update_fields=['telegram_chat_id'])
        self.buyer.features.notifications_telegram = True
        self.buyer.features.save(update_fields=['notifications_telegram'])

        tg_patch, _ = self._mock_telegram()
        with tg_patch, patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'fake-token'}):
            response = self.client.post(self._url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('telegram', response.data['sent_to'])

    def test_telegram_not_sent_when_feature_disabled(self):
        self.buyer.telegram_chat_id = 123456789
        self.buyer.save(update_fields=['telegram_chat_id'])
        # notifications_telegram defaults to False — no change needed

        tg_patch, mock_tg = self._mock_telegram()
        with tg_patch, patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'fake-token'}):
            response = self.client.post(self._url())

        mock_tg.Bot.assert_not_called()
        self.assertNotIn('telegram', response.data.get('sent_to', []))

    # ── WhatsApp ─────────────────────────────────────────────────────────────

    def test_sends_via_whatsapp_when_configured(self):
        self.buyer.features.notifications_whatsapp = True
        self.buyer.features.save(update_fields=['notifications_whatsapp'])

        with patch('my_iveco_crm.whatsapp.send_whatsapp_text') as mock_wa:
            response = self.client.post(self._url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('whatsapp', response.data['sent_to'])
        mock_wa.assert_called_once()

    def test_whatsapp_not_sent_when_feature_disabled(self):
        # notifications_whatsapp defaults to False
        with patch('my_iveco_crm.whatsapp.send_whatsapp_text') as mock_wa:
            self.client.post(self._url())

        mock_wa.assert_not_called()

    # ── Response structure ───────────────────────────────────────────────────

    def test_response_contains_declaration_number(self):
        self.buyer.features.notifications_whatsapp = True
        self.buyer.features.save(update_fields=['notifications_whatsapp'])

        with patch('my_iveco_crm.whatsapp.send_whatsapp_text'):
            response = self.client.post(self._url())

        self.assertEqual(response.data['declaration'], '20450000000001')

    def test_response_has_sent_to_and_errors_keys(self):
        self.buyer.features.notifications_whatsapp = True
        self.buyer.features.save(update_fields=['notifications_whatsapp'])

        with patch('my_iveco_crm.whatsapp.send_whatsapp_text'):
            response = self.client.post(self._url())

        self.assertIn('sent_to', response.data)
        self.assertIn('errors', response.data)
