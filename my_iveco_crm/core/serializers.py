# core/serializers.py

from rest_framework import serializers

from .models import Module


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = [
            'name', 'label', 'description',
            'is_enabled', 'is_core',
            'url_prefixes', 'dependencies',
            'order', 'updated_at',
        ]
        read_only_fields = [
            'name', 'is_core', 'url_prefixes',
            'dependencies', 'order', 'updated_at',
        ]
