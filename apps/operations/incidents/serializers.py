"""apps/operations/incidents/serializers.py — Serializers for Incident."""

from rest_framework import serializers

from apps.base.serializers import BaseSerializer
from apps.base.constants import UserRole
from apps.core.employees.models import Employee
from apps.operations.incidents.models import Incident


class IncidentSerializer(BaseSerializer):
    """Full serializer for Incident — all fields."""

    reported_by_name = serializers.SerializerMethodField()
    reported_by_employee_id = serializers.CharField(
        source="reported_by.employee_id", read_only=True,
    )
    assigned_to_name = serializers.SerializerMethodField()
    assigned_to_employee_id = serializers.CharField(
        source="assigned_to.employee_id", read_only=True,
    )
    asset_name = serializers.CharField(source="asset.name", read_only=True)
    asset_id_hrid = serializers.CharField(source="asset.asset_id", read_only=True)

    class Meta:
        model = Incident
        fields = [
            # BaseModel fields
            "id",
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
            "asset_id_hrid",
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
        if user and getattr(user, "role", None) == UserRole.EMPLOYEE.value:
            restricted = {"assigned_to", "resolution_notes", "status"}
            for field in restricted:
                if field in attrs:
                    raise serializers.ValidationError(
                        {field: f"Employees cannot modify {field}."}
                    )
        return attrs

    def get_reported_by_name(self, obj):
        if obj.reported_by and obj.reported_by.user:
            return obj.reported_by.user.get_full_name()
        return None

    def get_assigned_to_name(self, obj):
        if obj.assigned_to and obj.assigned_to.user:
            return obj.assigned_to.user.get_full_name()
        return None


class IncidentListSerializer(BaseSerializer):
    """Lightweight serializer for list views."""

    reported_by_name = serializers.SerializerMethodField()
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

    def get_reported_by_name(self, obj):
        if obj.reported_by and obj.reported_by.user:
            return obj.reported_by.user.get_full_name()
        return None


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
        if user and getattr(user, "role", None) != UserRole.SUPER_ADMIN.value:
            user_org = getattr(user, "organization", None)
            if user_org and asset and asset.organization_id != user_org.id:
                raise serializers.ValidationError(
                    {"asset": "This asset does not belong to your organization."}
                )
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
