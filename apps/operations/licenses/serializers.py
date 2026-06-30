"""apps/operations/licenses/serializers.py — Serializers for licenses."""

from rest_framework import serializers

from apps.base.fields import EmployeeNameField
from apps.base.serializers import BaseSerializer
from apps.assets.inventory.models import Asset
from apps.core.employees.models import Employee
from apps.operations.licenses.models import SoftwareLicense, LicenseAssignment


class SoftwareLicenseSerializer(BaseSerializer):
    """Full serializer for SoftwareLicense — all fields."""

    class Meta:
        model = SoftwareLicense
        fields = [
            # BaseModel fields
            "id",
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            # License fields
            "lic_id",
            "organization",
            "software_name",
            "license_key",
            "license_type",
            "total_seats",
            "used_seats",
            "available_seats",
            "expiry_date",
            "purchase_cost",
            "vendor",
            "document",
        ]
        read_only_fields = [
            "id",
            "lic_id",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "used_seats",
            "available_seats",
        ]

    def validate(self, attrs):
        """Employees cannot modify licenses. Enforce tenant isolation and seat limits."""
        request = self.context.get("request")
        user = request.user if request else None
        if user:
            if getattr(user, "is_employee", False):
                raise serializers.ValidationError(
                    "Employees cannot create or modify licenses."
                )
            if not getattr(user, "is_super_admin", False):
                user_org = getattr(user, "organization", None)
                org = attrs.get("organization")
                if user_org and org and org.id != user_org.id:
                    raise serializers.ValidationError(
                        {"organization": "Cannot modify a license for another organization."}
                    )

        # Prevent reducing total_seats below used_seats
        if self.instance and "total_seats" in attrs:
            if attrs["total_seats"] < self.instance.used_seats:
                raise serializers.ValidationError(
                    {"total_seats": f"Cannot reduce total seats below {self.instance.used_seats} (currently assigned)."}
                )
        return attrs


class SoftwareLicenseListSerializer(BaseSerializer):
    """Lightweight serializer for list views."""

    class Meta:
        model = SoftwareLicense
        fields = [
            "id",
            "lic_id",
            "software_name",
            "license_type",
            "total_seats",
            "used_seats",
            "available_seats",
            "expiry_date",
            "vendor",
            "organization",
            "created_at",
        ]


class LicenseAssignmentSerializer(BaseSerializer):
    """Full serializer for LicenseAssignment."""

    employee_name = EmployeeNameField(source="employee")
    employee_emp_id = serializers.CharField(
        source="employee.employee_id", read_only=True,
    )
    asset_name = serializers.CharField(source="asset.name", read_only=True)
    asset_id_hrid = serializers.CharField(source="asset.asset_id", read_only=True)
    license_name = serializers.CharField(source="license.software_name", read_only=True)
    lic_id = serializers.CharField(source="license.lic_id", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = LicenseAssignment
        fields = [
            # BaseModel fields
            "id",
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            # Assignment fields
            "license",
            "license_name",
            "lic_id",
            "organization",
            "employee",
            "employee_name",
            "employee_emp_id",
            "asset",
            "asset_name",
            "asset_id_hrid",
            "assigned_at",
            "revoked_at",
        ]
        read_only_fields = [
            "id",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "assigned_at",
            "revoked_at",
            "license",
            "organization",
        ]


class LicenseAssignSerializer(serializers.Serializer):
    """Serializer for assigning a license seat."""

    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        required=False,
        help_text="Employee ID to assign the license to",
    )
    asset = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects.all(),
        required=False,
        help_text="Asset ID to assign the license to",
    )

    def __init__(self, *args, **kwargs):
        employee_qs = kwargs.pop("employee_qs", None)
        asset_qs = kwargs.pop("asset_qs", None)
        super().__init__(*args, **kwargs)
        if employee_qs is not None:
            self.fields["employee"].queryset = employee_qs
        if asset_qs is not None:
            self.fields["asset"].queryset = asset_qs

    def validate(self, attrs):
        if not attrs.get("employee") and not attrs.get("asset"):
            raise serializers.ValidationError(
                "Provide at least one of: employee, asset."
            )
        return attrs


class LicenseUtilizationSerializer(serializers.Serializer):
    """Serializer for license utilization stats."""

    license_id = serializers.UUIDField()
    lic_id = serializers.CharField()
    software_name = serializers.CharField()
    total_seats = serializers.IntegerField()
    used_seats = serializers.IntegerField()
    available_seats = serializers.IntegerField()
    utilization_rate = serializers.FloatField()
    active_assignments = LicenseAssignmentSerializer(many=True)
