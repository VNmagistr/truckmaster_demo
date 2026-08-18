from rest_framework import serializers

from .models import ShortLink


class ShortLinkSerializer(serializers.ModelSerializer):
    has_qr = serializers.SerializerMethodField()

    class Meta:
        model = ShortLink
        fields = [
            'id', 'slug', 'label', 'target_url', 'full_url',
            'is_active', 'hits', 'has_qr', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'slug', 'target_url', 'full_url',
            'hits', 'has_qr', 'created_at', 'updated_at',
        ]

    def get_has_qr(self, obj):
        return bool(obj.qr_svg)
