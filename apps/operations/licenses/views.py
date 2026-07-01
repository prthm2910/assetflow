"""apps/operations/licenses/views.py — ViewSets for licenses."""

import logging

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.base.constants import UserRole
from apps.base.permissions import RoleBasedPermission
from apps.base.response import success_response, error_response
from apps.base.viewsets import BaseViewSet
from apps.assets.inventory.models import Asset
from apps.core.employees.models import Employee
from apps.operations.licenses.filters import SoftwareLicenseFilterSet, LicenseAssignmentFilterSet
from apps.operations.licenses.models import SoftwareLicense, LicenseAssignment
from apps.operations.licenses.serializers import (
    SoftwareLicenseSerializer,
    SoftwareLicenseListSerializer,
    LicenseAssignmentSerializer,
    LicenseAssignSerializer,
)

logger = logging.getLogger(__name__)


class SoftwareLicenseViewSet(BaseViewSet):
    """
    Software license management within an organization.

    - Super admin: full CRUD across all organizations
    - Org admin: full CRUD within their organization
    - Employee: read-only within their organization

    Custom actions:
        - assign: Assign a license seat to employee/asset
        - revoke: Revoke a license assignment
        - utilization: Get utilization stats for a license
        - assignments: List all assignments for a license
    """

    lookup_field = "lic_id"
    lookup_value_regex = r"[\w-]+"
    ordering_fields = ["created_at", "software_name", "expiry_date"]
    ordering = ["-created_at"]
    search_fields = ["software_name", "lic_id", "vendor", "license_key"]

    filterset_class = SoftwareLicenseFilterSet

    def get_permissions(self):
        """Action-level permissions."""
        if self.action in ("list", "retrieve", "utilization", "assignments"):
            return [IsAuthenticated()]
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [RoleBasedPermission(write_roles=[UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN])]
        if self.action in ("assign", "revoke"):
            return [RoleBasedPermission(write_roles=[UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN])]
        return super().get_permissions()

    def get_queryset(self):
        queryset = SoftwareLicense.objects.select_related("organization").annotate(
            annotated_used_seats=Count(
                "assignments",
                filter=Q(assignments__revoked_at__isnull=True),
            ),
        )
        return self.scope_queryset(queryset)

    def get_serializer_class(self):
        if self.action == "list":
            return SoftwareLicenseListSerializer
        return SoftwareLicenseSerializer

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, lic_id=None):
        """
        Assign a license seat to an employee and/or asset.

        Uses select_for_update to prevent race conditions on concurrent assignments.
        """
        instance = self.get_object()

        employee_qs = Employee.objects.filter(
            organization=instance.organization,
        ).active()
        asset_qs = Asset.objects.filter(
            organization=instance.organization,
        )
        serializer = LicenseAssignSerializer(
            data=request.data,
            context={"request": request},
            employee_qs=employee_qs,
            asset_qs=asset_qs,
        )
        serializer.is_valid(raise_exception=True)

        employee = serializer.validated_data.get("employee")
        asset = serializer.validated_data.get("asset")

        with transaction.atomic():
            # Lock the license record to prevent concurrent over-allocation
            locked_license = SoftwareLicense.objects.select_for_update().get(pk=instance.pk)
            if locked_license.available_seats <= 0:
                return error_response(
                    message="No available seats for this license.",
                    code="NO_SEATS_AVAILABLE",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # Prevent duplicate active assignments
            if employee and locked_license.assignments.filter(
                employee=employee, revoked_at__isnull=True
            ).exists():
                return error_response(
                    message="This employee already has an active assignment for this license.",
                    code="DUPLICATE_ASSIGNMENT",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if asset and locked_license.assignments.filter(
                asset=asset, revoked_at__isnull=True
            ).exists():
                return error_response(
                    message="This asset already has an active assignment for this license.",
                    code="DUPLICATE_ASSIGNMENT",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            assignment = LicenseAssignment.objects.create(
                organization=locked_license.organization,
                license=locked_license,
                employee=employee,
                asset=asset,
            )

        logger.info(
            "License %s assigned to %s by %s",
            locked_license.lic_id,
            employee.user.get_full_name() if employee else asset.name,
            request.user.email,
        )
        return success_response(
            data=LicenseAssignmentSerializer(assignment).data,
            message="License assigned successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, lic_id=None):
        """
        Revoke a license assignment.

        Expects assignment_id in request body.
        """
        instance = self.get_object()

        assignment_id = request.data.get("assignment_id")
        if not assignment_id:
            return error_response(
                message="assignment_id is required.",
                code="MISSING_FIELD",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            assignment = instance.assignments.get(pk=assignment_id)
        except LicenseAssignment.DoesNotExist:
            return error_response(
                message="Assignment not found.",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if not assignment.is_assignment_active:
            return error_response(
                message="This assignment is already revoked.",
                code="ALREADY_REVOKED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        assignment.revoked_at = timezone.now()
        assignment.updated_by = request.user
        assignment.save(update_fields=["revoked_at", "updated_at", "updated_by"])

        logger.info(
            "License assignment %s revoked by %s",
            assignment.pk,
            request.user.email,
        )
        return success_response(
            data=LicenseAssignmentSerializer(assignment).data,
            message="License assignment revoked.",
        )

    @action(detail=True, methods=["get"], url_path="utilization")
    def utilization(self, request, lic_id=None):
        """Get utilization stats for a license."""
        instance = self.get_object()
        total = instance.total_seats
        used = instance.used_seats
        rate = round((used / total * 100) if total > 0 else 0, 1)

        active_assignments = instance.assignments.filter(
            revoked_at__isnull=True
        ).select_related("employee", "employee__user", "asset")

        data = {
            "license_id": str(instance.id),
            "lic_id": instance.lic_id,
            "software_name": instance.software_name,
            "total_seats": total,
            "used_seats": used,
            "available_seats": instance.available_seats,
            "utilization_rate": rate,
            "active_assignments": LicenseAssignmentSerializer(
                active_assignments, many=True
            ).data,
        }

        return success_response(data=data)

    @action(detail=True, methods=["get"], url_path="assignments")
    def assignments(self, request, lic_id=None):
        """List all assignments for a license. Supports filtering."""
        instance = self.get_object()
        queryset = instance.assignments.select_related(
            "employee", "employee__user", "asset"
        )

        # Apply LicenseAssignmentFilterSet since viewset uses SoftwareLicenseFilterSet
        filterset = LicenseAssignmentFilterSet(request.GET, queryset=queryset)
        if filterset.is_valid():
            queryset = filterset.qs

        return self.paginated_response(queryset, LicenseAssignmentSerializer)
