from decimal import Decimal

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
