from django.db import models
from django.utils import timezone


def _next_invoice_number():
    year = timezone.now().year
    prefix = f'ЗЧ-{year}-'
    last = Invoice.objects.filter(number__startswith=prefix).order_by('-number').first()
    if last:
        try:
            seq = int(last.number.replace(prefix, '')) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f'{prefix}{seq:03d}'


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft',     'Чернетка'),
        ('sent',      'Виставлено'),
        ('paid',      'Оплачено'),
        ('cancelled', 'Скасовано'),
    ]

    number = models.CharField(
        max_length=30, unique=True,
        verbose_name='Номер рахунку',
    )
    client = models.ForeignKey(
        'clients.Client', on_delete=models.PROTECT,
        related_name='invoices', verbose_name='Клієнт',
    )
    truck = models.ForeignKey(
        'clients.Truck', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoices', verbose_name='Вантажівка',
    )
    date = models.DateField(default=timezone.localdate, verbose_name='Дата')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft',
        verbose_name='Статус',
    )
    nova_poshta_declaration = models.CharField(
        max_length=30, blank=True,
        verbose_name='Декларація Нової Пошти',
    )
    notes = models.TextField(blank=True, verbose_name='Примітки')
    total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Сума', editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Рахунок'
        verbose_name_plural = 'Рахунки на запчастини'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.number} — {self.client.name}'

    def recalc_total(self):
        from decimal import Decimal
        total = sum(
            (item.quantity * item.unit_price for item in self.items.all()),
            Decimal('0')
        )
        Invoice.objects.filter(pk=self.pk).update(total=total)
        self.total = total


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE,
        related_name='items', verbose_name='Рахунок',
    )
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='invoice_items', verbose_name='Товар',
    )
    description = models.CharField(max_length=255, verbose_name='Опис')
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=1,
        verbose_name='Кількість',
    )
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='Ціна за одиницю',
    )

    class Meta:
        verbose_name = 'Позиція рахунку'
        verbose_name_plural = 'Позиції рахунку'
        ordering = ['id']

    def __str__(self):
        return f'{self.description} × {self.quantity}'

    def save(self, *args, **kwargs):
        if self.product:
            if not self.description:
                self.description = self.product.name
            if not self.unit_price:
                self.unit_price = self.product.selling_price or 0
        super().save(*args, **kwargs)
        self.invoice.recalc_total()

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)
        invoice.recalc_total()
