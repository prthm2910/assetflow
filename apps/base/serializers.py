"""
apps/base/serializers.py — Base serializer for all AssetFlow models.

Provides:
- BaseModel fields as read-only (id, created_at, updated_at, created_by, updated_by, is_active, is_deleted)
- DRY field definitions for all child serializers
"""

from rest_framework import serializers


class BaseSerializer(serializers.ModelSerializer):
    """
    Base serializer for all AssetFlow models.

    Includes all BaseModel fields as read-only:
    - created_at / updated_at (timestamps)
    - created_by / updated_by (user FKs)
    - is_active / is_deleted (status flags)

    Usage:
        class AssetSerializer(BaseSerializer):
            class Meta:
                model = Asset
                fields = BaseSerializer.Meta.fields + ['asset_id', 'name', ...]

    Child serializers inherit these fields automatically.
    """

    # BaseModel fields as read-only
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    updated_by = serializers.PrimaryKeyRelatedField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_deleted = serializers.BooleanField(read_only=True)

    class Meta:
        abstract = True
