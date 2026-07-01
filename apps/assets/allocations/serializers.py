"""
apps/assets/allocations/serializers.py — Serializers for Allocation.
"""

from rest_framework import serializers

from apps.base.fields import EmployeeNameField
from apps.base.serializers import BaseSerializer
from apps.assets.allocations.models import Allocation
from apps.base.utils import validate_tenant_isolation_multi
from apps.core.employees.models import Employee


class AllocationSerializer(BaseSerializer):
    """Full serializer for Allocation — all fields."""

    asset_name = serializers.CharField(source="asset.name", read_only=True)
    asset_id_hrid = serializers.CharField(source="asset.asset_id", read_only=True)
    employee_name = EmployeeNameField(source="employee")
    employee_emp_id = serializers.CharField(source="employee.emp_id", read_only=True)
    allocated_by_name = serializers.SerializerMethodField()
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = Allocation
        fields = [
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
            "alloc_id",
            "allocated_at",
            "is_current",
            # Core fields cannot be modified after creation
            "organization",
            "asset",
            "employee",
        ]

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
    employee_name = EmployeeNameField(source="employee")
    employee_emp_id = serializers.CharField(source="employee.emp_id", read_only=True)
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = Allocation
        fields = [
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
            "alloc_id",
            "asset",
            "employee",
            "notes",
        ]
        read_only_fields = [
            "alloc_id",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None
        asset = attrs.get("asset")
        employee = attrs.get("employee")

        # Tenant isolation — non-super-admins can only allocate within their org
        if user:
            

            validate_tenant_isolation_multi(user, [
                ("asset", asset, "asset"),
                ("employee", employee, "employee"),
            ])

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
