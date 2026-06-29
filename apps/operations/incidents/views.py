"""apps/operations/incidents/views.py — ViewSets for Incident."""

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.base.constants import UserRole
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
        employee = getattr(user, "employee_profile", None)
        if employee:
            return queryset.filter(reported_by=employee)
        return queryset.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return success_response(
                data=self.get_paginated_response(serializer.data).data
            )
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(data=serializer.data)

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
        user_org = getattr(user, "organization", None)

        # Resolve asset to get its organization for super admin path
        asset_id = data.get("asset")
        if asset_id and user_org is None:
            from apps.assets.inventory.models import Asset

            try:
                asset_obj = Asset.objects.select_related("organization").get(pk=asset_id)
                report_org = asset_obj.organization
            except Asset.DoesNotExist:
                report_org = None
        else:
            report_org = user_org

        # Resolve reported_by from the current user's employee profile
        employee = getattr(user, "employee_profile", None)
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

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()  # soft-delete
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, inc_id=None):
        """
        Assign an incident to an employee.

        Transitions status from 'reported' to 'open' if still reported.
        """
        instance = self.get_object()

        employee_qs = Employee.objects.filter(
            organization=instance.organization,
            is_active=True,
            is_deleted=False,
        )
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
        """
        Transition incident from open to in_progress.
        """
        instance = self.get_object()

        if instance.status != IncidentStatus.OPEN.value:
            return Response(
                {"error": f"Only open incidents can be started. Current status: {instance.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.status = IncidentStatus.IN_PROGRESS.value
        instance.updated_by = request.user
        instance.save(update_fields=["status", "updated_at", "updated_by"])

        return success_response(
            data=IncidentSerializer(instance).data,
            message="Incident work started.",
        )

    @action(detail=True, methods=["post"], url_path="resolve")
    def resolve(self, request, inc_id=None):
        """
        Mark an incident as resolved.

        Requires the incident to be in progress. Sets resolved_at timestamp.
        """
        instance = self.get_object()

        if instance.status != IncidentStatus.IN_PROGRESS.value:
            return Response(
                {"error": f"Only in_progress incidents can be resolved. Current status: {instance.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
        """
        Close a resolved incident.

        Requires the incident to be resolved. Sets closed_at timestamp.
        """
        instance = self.get_object()

        if instance.status != IncidentStatus.RESOLVED.value:
            return Response(
                {"error": f"Only resolved incidents can be closed. Current status: {instance.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
