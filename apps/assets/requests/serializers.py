"""
apps/assets/requests/serializers.py — Serializers for AssetRequest.
"""

from rest_framework import serializers

from apps.base.serializers import BaseSerializer
from apps.base.constants import UserRole, RequestStatus
from apps.assets.requests.models import AssetRequest


class AssetRequestSerializer(BaseSerializer):
    """Full serializer for AssetRequest — all fields."""

    requested_by_name = serializers.SerializerMethodField()
    requested_by_emp_id = serializers.CharField(
        source="requested_by.emp_id", read_only=True
    )
    asset_category_name = serializers.CharField(
        source="asset_category.name", read_only=True
    )
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AssetRequest
        fields = [
            # BaseModel fields
            "id",
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            # AssetRequest fields
            "req_id",
            "organization",
            "requested_by",
            "requested_by_name",
            "requested_by_emp_id",
            "asset_category",
            "asset_category_name",
            "reason",
            "priority",
            "status",
            "reviewed_by",
            "reviewed_by_name",
            "review_notes",
            "reviewed_at",
        ]
        read_only_fields = [
            "id",
            "req_id",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "reviewed_by",
            "reviewed_at",
            # Core immutable fields
            "organization",
            "requested_by",
            "asset_category",
        ]

    def get_requested_by_name(self, obj):
        if obj.requested_by and obj.requested_by.user:
            return obj.requested_by.user.get_full_name()
        return None

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name()
        return None


class AssetRequestListSerializer(BaseSerializer):
    """Lightweight serializer for list views."""

    requested_by_name = serializers.SerializerMethodField()
    requested_by_emp_id = serializers.CharField(
        source="requested_by.emp_id", read_only=True
    )
    asset_category_name = serializers.CharField(
        source="asset_category.name", read_only=True
    )

    class Meta:
        model = AssetRequest
        fields = [
            "id",
            "req_id",
            "requested_by",
            "requested_by_name",
            "requested_by_emp_id",
            "asset_category",
            "asset_category_name",
            "reason",
            "priority",
            "status",
            "reviewed_at",
            "organization",
            "created_at",
        ]

    def get_requested_by_name(self, obj):
        if obj.requested_by and obj.requested_by.user:
            return obj.requested_by.user.get_full_name()
        return None


class AssetRequestCreateSerializer(BaseSerializer):
    """
    Serializer for employees to submit a new asset request.

    The view injects `organization` and `requested_by` from the request context.
    """

    class Meta:
        model = AssetRequest
        fields = [
            "id",
            "req_id",
            "requested_by",
            "asset_category",
            "reason",
            "priority",
            "status",
            "created_by",
            "updated_by",
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "req_id",
            "requested_by",
            "status",
            "created_by",
            "updated_by",
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None
        category = attrs.get("asset_category")

        # Tenant isolation — non-super-admins can only request within their org
        if user and getattr(user, "role", None) != UserRole.SUPER_ADMIN.value:
            user_org = getattr(user, "organization", None)
            if user_org and category and category.organization_id != user_org.id:
                raise serializers.ValidationError(
                    {"asset_category": "This category does not belong to your organization."}
                )
        return attrs


class ApproveRejectSerializer(serializers.Serializer):
    """Serializer for approve/reject review actions."""

    review_notes = serializers.CharField(required=False, allow_blank=True, default="")
