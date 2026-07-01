"""
apps/assets/allocations/views.py — ViewSets for Allocation.
"""

import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.base.constants import UserRole
from apps.assets.inventory.constants import AssetStatus
from apps.assets.inventory.models import Asset
from apps.assets.inventory.services import AssetService
from apps.base.response import success_response, error_response
from apps.base.viewsets import BaseViewSet
from apps.assets.allocations.filters import AllocationFilterSet
from apps.assets.allocations.models import Allocation
from apps.assets.allocations.serializers import (
    AllocationSerializer,
    AllocationListSerializer,
    AllocationCreateSerializer,
    TransferSerializer,
)

logger = logging.getLogger(__name__)


class AllocationViewSet(BaseViewSet):
    """
    Allocation management within an organization.

    - Super admin: full CRUD across all organizations
    - Org admin: full CRUD within their organization
    - Employee: read-only within their organization (their own allocations)

    Custom actions:
        - transfer: Transfer an asset from one employee to another
        - return_asset: Mark an active allocation as returned
        - current: List only active (unreturned) allocations

    Permissions:
        - Read (GET): Any authenticated user in the org
        - Write (POST/PUT/PATCH/DELETE): Org admin + Super admin
    """

    lookup_field = "alloc_id"
    lookup_value_regex = r"[\w-]+"
    ordering_fields = ["allocated_at", "created_at", "asset__name", "employee__user__first_name"]
    ordering = ["-allocated_at"]
    search_fields = [
        "asset__name", "asset__asset_id",
        "employee__user__first_name", "employee__user__last_name",
        "notes",
    ]

    filterset_class = AllocationFilterSet
    write_roles = [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]

    def get_queryset(self):
        """Select related fields and apply role-based scoping."""
        queryset = Allocation.objects.select_related(
            "organization", "asset", "employee", "employee__user", "allocated_by"
        )
        return self.scope_queryset(queryset)

    def get_serializer_class(self):
        if self.action == "list":
            return AllocationListSerializer
        if self.action == "create":
            return AllocationCreateSerializer
        return AllocationSerializer

    def scope_for_employee(self, queryset):
        """Employees see only allocations for their own employee record."""
        user = self.request.user
        employee = user.employee
        if employee:
            return queryset.filter(employee=employee)
        return queryset.none()

    def create(self, request, *args, **kwargs):
        """Allocate an asset to an employee. Updates asset status to 'allocated'."""
        data = request.data.copy()
        user = request.user
        asset_id = data.get("asset")

        alloc_org = AssetService.resolve_organization(
            user, related_model=Asset, related_id=asset_id
        )

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        # All DB writes in a single transaction
        with transaction.atomic():
            allocation = serializer.save(
                organization=alloc_org,
                allocated_by=request.user,
            )
            asset = allocation.asset
            update_fields = ["status", "updated_at", "updated_by"]
            asset.status = AssetStatus.ALLOCATED.value
            asset.save(update_fields=update_fields)

        logger.info(
            "Asset %s allocated to %s by %s",
            asset.asset_id,
            allocation.employee.user.get_full_name(),
            request.user.email,
        )
        return success_response(
            data=AllocationSerializer(allocation).data,
            message="Asset allocated successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # is_current checks returned_at — not the BaseModel soft-delete flag
        if instance.is_current:
            asset = instance.asset
            update_fields = ["status", "updated_at", "updated_by"]
            if hasattr(asset, "updated_by"):
                asset.updated_by = request.user
            asset.status = AssetStatus.AVAILABLE.value
            with transaction.atomic():
                asset.save(update_fields=update_fields)
                instance.delete()  # soft-delete
        else:
            instance.delete()  # soft-delete
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        """List only active (unreturned) allocations."""
        queryset = self.filter_queryset(
            self.get_queryset().filter(returned_at__isnull=True)
        )
        return self.paginated_response(queryset, self.get_serializer_class())

    @action(detail=True, methods=["post"], url_path="transfer")
    def transfer(self, request, alloc_id=None):
        """
        Transfer an asset from its current holder to a different employee.

        Closes the current allocation (sets returned_at) and creates a new
        active allocation for the new employee. The asset status remains 'allocated'.
        """
        current_allocation = self.get_object()

        if not current_allocation.is_current:
            return error_response(
                message="This allocation is already returned.",
                code="ALREADY_RETURNED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_employee = serializer.validated_data["employee"]
        transfer_notes = serializer.validated_data.get("notes", "")

        # Cross-org guard — target employee must be in the same org as the allocation
        if new_employee.organization != current_allocation.organization:
            return error_response(
                message="Cannot transfer to an employee of a different organization.",
                code="CROSS_ORG_TRANSFER",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()

        # Defensive: safe employee name for notes
        current_emp_name = (
            current_allocation.employee.user.get_full_name()
            if getattr(current_allocation.employee, "user", None)
            else "Unknown Employee"
        )

        with transaction.atomic():
            # Close the current allocation
            current_allocation.returned_at = now
            current_allocation.updated_by = request.user
            current_allocation.save(
                update_fields=["returned_at", "updated_at", "updated_by"]
            )

            # Create new allocation for the new employee
            new_allocation = Allocation.objects.create(
                organization=current_allocation.organization,
                asset=current_allocation.asset,
                employee=new_employee,
                allocated_by=request.user,
                notes=transfer_notes or f"Transferred from {current_emp_name}.",
            )

        logger.info(
            "Asset %s transferred from %s to %s by %s",
            current_allocation.asset.asset_id,
            current_emp_name,
            new_employee.user.get_full_name(),
            request.user.email,
        )
        return success_response(
            data=AllocationSerializer(new_allocation).data,
            message=f"Asset transferred to {new_employee.user.get_full_name()}.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="return")
    def return_asset(self, request, alloc_id=None):
        """
        Mark an asset as returned.

        Sets returned_at on the active allocation and reverts the asset's
        status back to 'available'.
        """
        instance = self.get_object()

        if not instance.is_current:
            return error_response(
                message="This asset has already been returned.",
                code="ALREADY_RETURNED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        notes = request.data.get("notes", "")
        now = timezone.now()

        with transaction.atomic():
            # Close the allocation
            instance.returned_at = now
            instance.updated_by = request.user
            update_fields = ["returned_at", "updated_at", "updated_by"]
            if notes:
                instance.notes = f"{instance.notes}\n{notes}".strip()
                update_fields.append("notes")
            instance.save(update_fields=update_fields)

            # Revert asset status to 'available'
            asset = instance.asset
            update_fields = ["status", "updated_at"]
            if hasattr(asset, "updated_by"):
                asset.updated_by = request.user
                update_fields.append("updated_by")
            asset.status = AssetStatus.AVAILABLE.value
            asset.save(update_fields=update_fields)

        logger.info(
            "Asset %s returned by %s",
            asset.asset_id,
            request.user.email,
        )
        return success_response(
            data=AllocationSerializer(instance).data,
            message="Asset returned successfully.",
        )
