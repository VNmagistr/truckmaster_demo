from rest_framework import serializers
from .models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku  = serializers.CharField(source='product.sku_code', read_only=True)
    total        = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceItem
        fields = [
            'id', 'invoice', 'product', 'product_name', 'product_sku',
            'description', 'quantity', 'unit_price', 'total',
        ]
        read_only_fields = ['id', 'product_name', 'product_sku', 'total']

    def get_total(self, obj):
        return float(obj.quantity * obj.unit_price)


class InvoiceSerializer(serializers.ModelSerializer):
    client_name    = serializers.CharField(source='client.name', read_only=True)
    client_phone   = serializers.CharField(source='client.phone', read_only=True)
    truck_display  = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items          = InvoiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'number', 'client', 'client_name', 'client_phone',
            'truck', 'truck_display', 'date', 'status', 'status_display',
            'nova_poshta_declaration', 'notes', 'total', 'items', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'number', 'total', 'created_at', 'updated_at',
                            'client_name', 'client_phone', 'truck_display',
                            'status_display', 'items']

    def get_truck_display(self, obj):
        if not obj.truck:
            return None
        return f'{obj.truck.license_plate} — {obj.truck.specific_model_name}'


class InvoiceListSerializer(serializers.ModelSerializer):
    """Легкий серіалізатор для списку."""
    client_name    = serializers.CharField(source='client.name', read_only=True)
    truck_display  = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items_count    = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'number', 'client', 'client_name',
            'truck', 'truck_display', 'date', 'status', 'status_display',
            'total', 'items_count', 'created_at',
        ]
        read_only_fields = fields

    def get_truck_display(self, obj):
        if not obj.truck:
            return None
        return f'{obj.truck.license_plate}'

    def get_items_count(self, obj):
        return obj.items.count()
