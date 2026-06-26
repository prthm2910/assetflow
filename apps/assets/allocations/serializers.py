"""
apps/assets/allocations/serializers.py — Serializers for Allocation.
"""

from rest_framework import serializers

from apps.base.serializers import BaseSerializer
from apps.assets.inventory.models import Asset
from apps.assets.inventory.serializers import AssetListSerializer
from apps.assets.allocations.models import Allocation
from apps.core.employees.models import Employee


class AllocationSerializer(BaseSerializer):
    """Full serializer for Allocation — all fields."""

    asset_name = serializers.CharField(source="asset.name", read_only=True)
    asset_id_hrid = serializers.CharField(source="asset.asset_id", read_only=True)
    employee_name = serializers.SerializerMethodField()
    employee_emp_id = serializers.CharField(source="employee.emp_id", read_only=True)
    allocated_by_name = serializers.SerializerMethodField()
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = Allocation
        fields = [
            # BaseModel fields
            "id",
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            # Allocation fields
            "alloc_id",
            "organization",
            "asset",
            "asset_name",
            "asset_id_hrid",
            "employee",
            "employee_name",
            "employee_emp_id",
            "allocated_by",
            "allocated_by_name",
            "allocated_at",
            "returned_at",
            "notes",
            "is_current",
        ]
        read_only_fields = [
            "id",
            "alloc_id",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "allocated_at",
            "is_current",
        ]

    def get_employee_name(self, obj):
        if obj.employee and obj.employee.user:
            return obj.employee.user.get_full_name()
        return None

    def get_allocated_by_name(self, obj):
        if obj.allocated_by:
            return obj.allocated_by.get_full_name()
        return None

    def get_is_current(self, obj):
        return obj.is_current


class AllocationListSerializer(BaseSerializer):
    """Lightweight serializer for list views."""

    asset_name = serializers.CharField(source="asset.name", read_only=True)
    asset_id_hrid = serializers.CharField(source="asset.asset_id", read_only=True)
    employee_name = serializers.SerializerMethodField()
    employee_emp_id = serializers.CharField(source="employee.emp_id", read_only=True)
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = Allocation
        fields = [
            "id",
            "alloc_id",
            "asset",
            "asset_name",
            "asset_id_hrid",
            "employee",
            "employee_name",
            "employee_emp_id",
            "allocated_at",
            "returned_at",
            "is_current",
            "organization",
        ]

    def get_employee_name(self, obj):
        if obj.employee and obj.employee.user:
            return obj.employee.user.get_full_name()
        return None

    def get_is_current(self, obj):
        return obj.is_current


class AllocationCreateSerializer(BaseSerializer):
    """Serializer for creating a new allocation.

    Note: `organization` is excluded here — the view's create() enforces tenant
    isolation by injecting the caller's organization from the request context.
    """

    class Meta:
        model = Allocation
        fields = [
            "id",
            "alloc_id",
            "asset",
            "employee",
            "notes",
            "created_by",
            "updated_by",
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "alloc_id",
            "created_by",
            "updated_by",
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        asset = attrs.get("asset")
        # Check for active allocation in DB (authoritative source)
        has_active_allocation = Allocation.objects.filter(
            asset=asset, returned_at__isnull=True
        ).exists()
        if has_active_allocation:
            raise serializers.ValidationError(
                {"asset": "This asset is already allocated. Return it first."}
            )
        if asset.status == "retired":
            raise serializers.ValidationError(
                {"asset": "Retired assets cannot be allocated."}
            )
        if not asset.is_active:
            raise serializers.ValidationError(
                {"asset": "Inactive assets cannot be allocated."}
            )
        return attrs


class TransferSerializer(serializers.Serializer):
    """Serializer for transferring an asset to a different employee."""

    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        help_text="Employee ID (emp_id HRID) to transfer the asset to",
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
