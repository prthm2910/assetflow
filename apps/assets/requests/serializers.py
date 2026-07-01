"""
apps/assets/requests/serializers.py — Serializers for AssetRequest.
"""

from rest_framework import serializers

from apps.base.fields import EmployeeNameField
from apps.base.serializers import BaseSerializer
from apps.assets.requests.models import AssetRequest
from apps.base.utils import validate_tenant_isolation


class AssetRequestSerializer(BaseSerializer):
    """Full serializer for AssetRequest — all fields."""

    requested_by_name = EmployeeNameField(source="requested_by")
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
            "req_id",
            "reviewed_by",
            "reviewed_at",
            # Core immutable fields
            "organization",
            "requested_by",
            "asset_category",
            # Employees cannot bypass the formal workflow by patching status
            "status",
        ]

    def validate(self, attrs):
        """Employees cannot modify review_notes via PATCH."""
        request = self.context.get("request")
        user = request.user if request else None
        if user and getattr(user, "is_employee", False):
            if "review_notes" in attrs and attrs["review_notes"]:
                raise serializers.ValidationError(
                    {"review_notes": "Employees cannot modify review notes."}
                )
        return attrs

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name()
        return None


class AssetRequestListSerializer(BaseSerializer):
    """Lightweight serializer for list views."""

    requested_by_name = EmployeeNameField(source="requested_by")
    requested_by_emp_id = serializers.CharField(
        source="requested_by.emp_id", read_only=True
    )
    asset_category_name = serializers.CharField(
        source="asset_category.name", read_only=True
    )

    class Meta:
        model = AssetRequest
        fields = [
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
        ]


class AssetRequestCreateSerializer(BaseSerializer):
    """
    Serializer for employees to submit a new asset request.

    The view injects `organization` and `requested_by` from the request context.
    """

    class Meta:
        model = AssetRequest
        fields = [
            "req_id",
            "requested_by",
            "asset_category",
            "reason",
            "priority",
            "status",
        ]
        read_only_fields = [
            "req_id",
            "requested_by",
            "status",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None
        category = attrs.get("asset_category")

        # Tenant isolation — non-super-admins can only request within their org
        if user:
            

            validate_tenant_isolation(user, "asset_category", category, "category")
        return attrs


class ApproveRejectSerializer(serializers.Serializer):
    """Serializer for approve/reject review actions."""

    review_notes = serializers.CharField(required=False, allow_blank=True, default="")
