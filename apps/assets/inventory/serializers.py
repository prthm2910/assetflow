"""
apps/assets/inventory/serializers.py — Serializers for Asset.
"""

from rest_framework import serializers

from apps.base.constants import AssetStatus
from apps.base.serializers import BaseSerializer
from apps.assets.inventory.models import Asset


class AssetSerializer(BaseSerializer):
    """Full serializer for Asset — all fields."""

    category_name = serializers.CharField(
        source="category.name", read_only=True, allow_null=True
    )
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = [
            # BaseModel fields (read-only from BaseSerializer)
            "id",
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            # Asset fields
            "asset_id",
            "organization",
            "category",
            "category_name",
            "name",
            "description",
            "serial_number",
            "brand",
            "model_name",
            "purchase_date",
            "purchase_cost",
            "warranty_expiry",
            "status",
            "assigned_to",
            "assigned_to_name",
            "location",
        ]
        read_only_fields = [
            "id",
            "asset_id",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]

    def get_assigned_to_name(self, obj):
        if obj.assigned_to and obj.assigned_to.user:
            return obj.assigned_to.user.get_full_name()
        return None


class AssetListSerializer(BaseSerializer):
    """Lightweight serializer for list views."""

    category_name = serializers.CharField(
        source="category.name", read_only=True, allow_null=True
    )
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = [
            # BaseModel fields (read-only from BaseSerializer)
            "id",
            "is_active",
            "created_at",
            # Asset fields
            "asset_id",
            "name",
            "organization",
            "category",
            "category_name",
            "status",
            "assigned_to",
            "assigned_to_name",
            "location",
        ]
        # is_deleted inherited read-only from BaseSerializer

    def get_assigned_to_name(self, obj):
        if obj.assigned_to and obj.assigned_to.user:
            return obj.assigned_to.user.get_full_name()
        return None


class AssetStatusChangeSerializer(serializers.Serializer):
    """Serializer for changing an asset's status."""

    status = serializers.ChoiceField(choices=AssetStatus.choices())
