"""apps/operations/incidents/serializers.py — Serializers for Incident."""

from rest_framework import serializers

from apps.base.fields import EmployeeNameField
from apps.base.serializers import BaseSerializer
from apps.core.employees.models import Employee
from apps.operations.incidents.models import Incident
from apps.base.utils import validate_tenant_isolation


class IncidentSerializer(BaseSerializer):
    """Full serializer for Incident — all fields."""

    reported_by_name = EmployeeNameField(source="reported_by")
    reported_by_employee_id = serializers.CharField(
        source="reported_by.employee_id", read_only=True,
    )
    assigned_to_name = EmployeeNameField(source="assigned_to")
    assigned_to_employee_id = serializers.CharField(
        source="assigned_to.employee_id", read_only=True,
    )
    asset_name = serializers.CharField(source="asset.name", read_only=True)
    asset_id = serializers.CharField(source="asset.asset_id", read_only=True)

    class Meta:
        model = Incident
        fields = [
            # BaseModel fields
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            # Incident fields
            "inc_id",
            "organization",
            "asset",
            "asset_name",
            "asset_id",
            "reported_by",
            "reported_by_name",
            "reported_by_employee_id",
            "title",
            "description",
            "category",
            "status",
            "assigned_to",
            "assigned_to_name",
            "assigned_to_employee_id",
            "resolution_notes",
            "attachments",
            "resolved_at",
            "closed_at",
        ]
        read_only_fields = [
            "id",
            "inc_id",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "resolved_at",
            "closed_at",
            "status",
            # Core immutable fields
            "organization",
            "reported_by",
            "asset",
        ]

    def validate(self, attrs):
        """Employees cannot modify review-level fields via PATCH."""
        request = self.context.get("request")
        user = request.user if request else None
        if user and getattr(user, "is_employee", False):
            restricted = {"assigned_to", "resolution_notes", "status"}
            for field in restricted:
                if field in attrs:
                    raise serializers.ValidationError(
                        {field: f"Employees cannot modify {field}."}
                    )
        return attrs


class IncidentListSerializer(BaseSerializer):
    """Lightweight serializer for list views."""

    reported_by_name = EmployeeNameField(source="reported_by")
    reported_by_employee_id = serializers.CharField(
        source="reported_by.employee_id", read_only=True,
    )
    asset_name = serializers.CharField(source="asset.name", read_only=True)
    asset_id = serializers.CharField(source="asset.asset_id", read_only=True)

    class Meta:
        model = Incident
        fields = [
            "id",
            "inc_id",
            "asset",
            "asset_name",
            "asset_id",
            "reported_by",
            "reported_by_name",
            "reported_by_employee_id",
            "title",
            "category",
            "status",
            "assigned_to",
            "created_at",
            "organization",
        ]


class IncidentCreateSerializer(BaseSerializer):
    """
    Serializer for employees to submit a new incident.

    The view injects `organization` and `reported_by` from the request context.
    """

    class Meta:
        model = Incident
        fields = [
            "id",
            "inc_id",
            "asset",
            "reported_by",
            "title",
            "description",
            "category",
            "status",
            "assigned_to",
            "resolution_notes",
            "attachments",
            "resolved_at",
            "closed_at",
            "created_by",
            "updated_by",
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "inc_id",
            "reported_by",
            "status",
            "assigned_to",
            "resolution_notes",
            "resolved_at",
            "closed_at",
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
        asset = attrs.get("asset")

        # Tenant isolation — non-super-admins can only report within their org
        if user:
            

            validate_tenant_isolation(user, "asset", asset, "asset")
        return attrs


class AssignSerializer(serializers.Serializer):
    """Serializer for assigning an incident to an employee."""

    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        help_text="Employee ID to assign the incident to",
    )

    def __init__(self, *args, **kwargs):
        employee_qs = kwargs.pop("employee_qs", None)
        super().__init__(*args, **kwargs)
        if employee_qs is not None:
            self.fields["assigned_to"].queryset = employee_qs


class ResolveSerializer(serializers.Serializer):
    """Serializer for resolving an incident."""

    resolution_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class CloseSerializer(serializers.Serializer):
    """Serializer for closing an incident."""

    close_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
