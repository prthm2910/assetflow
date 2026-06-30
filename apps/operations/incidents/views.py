"""apps/operations/incidents/views.py — ViewSets for Incident."""

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.base.constants import UserRole
from apps.assets.inventory.models import Asset
from apps.assets.inventory.services import AssetService
from apps.operations.incidents.constants import IncidentStatus
from apps.base.permissions import RoleBasedPermission
from apps.base.response import success_response
from apps.base.viewsets import BaseViewSet
from apps.core.employees.models import Employee
from apps.operations.incidents.filters import IncidentFilterSet
from apps.operations.incidents.models import Incident
from apps.operations.incidents.serializers import (
    IncidentSerializer,
    IncidentListSerializer,
    IncidentCreateSerializer,
    AssignSerializer,
    ResolveSerializer,
    CloseSerializer,
)


class IncidentViewSet(BaseViewSet):
    """
    Incident management within an organization.

    - Super admin: full CRUD across all organizations
    - Org admin: full CRUD within their organization
    - Employee: read-only (their own incidents); report new incidents

    Org isolation is enforced at the queryset level by scope_queryset().
    Custom action permissions are defined in get_permissions().

    Custom actions:
        - report: any authenticated user in their org
        - assign: org admin or super admin
        - resolve: org admin or super admin
        - close: org admin or super admin
        - add_attachment: org admin or super admin
    """

    lookup_field = "inc_id"
    lookup_value_regex = r"[\w-]+"
    ordering_fields = [
        "created_at",
        "status",
        "category",
        "asset__name",
        "reported_by__user__first_name",
    ]
    ordering = ["-created_at"]
    search_fields = [
        "title",
        "description",
        "inc_id",
        "asset__name",
        "asset__asset_id",
        "reported_by__user__first_name",
        "reported_by__user__last_name",
    ]

    filterset_class = IncidentFilterSet

    def get_permissions(self):
        """Action-level permissions — org isolation via scope_queryset."""
        # Standard read: any authenticated user
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        # report: any authenticated user in their org
        if self.action == "report":
            return [IsAuthenticated()]
        # create/update/partial_update/destroy: org admin + super admin only
        # Employees can only report new incidents, not modify existing ones
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [RoleBasedPermission(write_roles=[UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN])]
        # assign/resolve/close/add_attachment: org admin or super admin
        if self.action in ("assign", "resolve", "close", "add_attachment", "start_work"):
            return [RoleBasedPermission(write_roles=[UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN])]
        # Default: same as super() — write_roles enforced
        return super().get_permissions()

    def get_queryset(self):
        """Select related fields and apply role-based scoping."""
        queryset = Incident.objects.select_related(
            "organization",
            "asset",
            "reported_by",
            "reported_by__user",
            "assigned_to",
            "assigned_to__user",
        )
        return self.scope_queryset(queryset)

    def get_serializer_class(self):
        if self.action == "list":
            return IncidentListSerializer
        if self.action == "create" or self.action == "report":
            return IncidentCreateSerializer
        return IncidentSerializer

    def scope_for_employee(self, queryset):
        """Employees see only incidents they reported."""
        user = self.request.user
        employee = user.employee
        if employee:
            return queryset.filter(reported_by=employee)
        return queryset.none()

    def create(self, request, *args, **kwargs):
        """Create a new incident. Internal admin endpoint."""
        return self._report(request)

    @action(detail=False, methods=["post"], url_path="report")
    def report(self, request):
        """
        Report a new incident (employee-facing action).

        Sets `reported_by` to the current user's employee profile and
        `organization` to their organization.
        """
        return self._report(request)

    def _report(self, request):
        """Shared create logic for both create and report actions."""
        data = request.data.copy()
        user = request.user
        asset_id = data.get("asset")

        report_org = AssetService.resolve_organization(
            user, related_model=Asset, related_id=asset_id
        )

        # Resolve reported_by from the current user's employee profile
        employee = user.employee
        if not employee:
            return Response(
                {"error": "No employee profile found for the current user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            organization=report_org,
            reported_by=employee,
            status=IncidentStatus.REPORTED.value,
        )

        return success_response(
            data=IncidentSerializer(serializer.instance).data,
            message="Incident reported successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, inc_id=None):
        """
        Assign an incident to an employee.

        Transitions status from 'reported' to 'open' if still reported.
        """
        instance = self.get_object()

        employee_qs = Employee.objects.filter(
            organization=instance.organization,
        ).active()
        serializer = AssignSerializer(
            data=request.data,
            context={"request": request},
            employee_qs=employee_qs,
        )
        serializer.is_valid(raise_exception=True)

        # Transition reported → open on assignment
        if instance.status == IncidentStatus.REPORTED.value:
            instance.status = IncidentStatus.OPEN.value

        instance.assigned_to = serializer.validated_data["assigned_to"]
        instance.updated_by = request.user
        instance.save(
            update_fields=[
                "status",
                "assigned_to",
                "updated_at",
                "updated_by",
            ]
        )

        return success_response(
            data=IncidentSerializer(instance).data,
            message="Incident assigned successfully.",
        )

    @action(detail=True, methods=["post"], url_path="start")
    def start_work(self, request, inc_id=None):
        """Transition incident from open to in_progress."""
        instance = self.get_object()

        err = self.require_status(instance, IncidentStatus.OPEN.value, "started")
        if err:
            return err

        instance.status = IncidentStatus.IN_PROGRESS.value
        instance.updated_by = request.user
        instance.save(update_fields=["status", "updated_at", "updated_by"])

        return success_response(
            data=IncidentSerializer(instance).data,
            message="Incident work started.",
        )

    @action(detail=True, methods=["post"], url_path="resolve")
    def resolve(self, request, inc_id=None):
        """Mark an incident as resolved."""
        instance = self.get_object()

        err = self.require_status(instance, IncidentStatus.IN_PROGRESS.value, "resolved")
        if err:
            return err

        serializer = ResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        now = timezone.now()
        instance.status = IncidentStatus.RESOLVED.value
        instance.resolved_at = now
        instance.resolution_notes = serializer.validated_data.get(
            "resolution_notes", instance.resolution_notes
        )
        instance.updated_by = request.user
        instance.save(
            update_fields=[
                "status",
                "resolved_at",
                "resolution_notes",
                "updated_at",
                "updated_by",
            ]
        )

        return success_response(
            data=IncidentSerializer(instance).data,
            message="Incident resolved successfully.",
        )

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, inc_id=None):
        """Close a resolved incident."""
        instance = self.get_object()

        err = self.require_status(instance, IncidentStatus.RESOLVED.value, "closed")
        if err:
            return err

        serializer = CloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        now = timezone.now()
        instance.status = IncidentStatus.CLOSED.value
        instance.closed_at = now
        if serializer.validated_data.get("close_notes"):
            instance.resolution_notes = (
                f"{instance.resolution_notes}\n{serializer.validated_data['close_notes']}".strip()
            )
        instance.updated_by = request.user
        instance.save(
            update_fields=[
                "status",
                "closed_at",
                "resolution_notes",
                "updated_at",
                "updated_by",
            ]
        )

        return success_response(
            data=IncidentSerializer(instance).data,
            message="Incident closed successfully.",
        )

    @action(detail=True, methods=["post"], url_path="attachments")
    def add_attachment(self, request, inc_id=None):
        """
        Add an attachment URL to the incident.

        Expects JSON body: {"attachment_url": "https://..."}
        """
        instance = self.get_object()

        attachment_url = request.data.get("attachment_url")
        if not attachment_url:
            return Response(
                {"error": "attachment_url is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        attachments = instance.attachments or []
        attachments.append(attachment_url)
        instance.attachments = attachments
        instance.updated_by = request.user
        instance.save(update_fields=["attachments", "updated_at", "updated_by"])

        return success_response(
            data=IncidentSerializer(instance).data,
            message="Attachment added successfully.",
        )
