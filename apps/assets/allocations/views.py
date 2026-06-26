"""
apps/assets/allocations/views.py — ViewSets for Allocation.
"""

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.base.constants import UserRole, AssetStatus
from apps.base.response import success_response
from apps.base.viewsets import BaseViewSet
from apps.assets.allocations.filters import AllocationFilterSet
from apps.assets.allocations.models import Allocation
from apps.assets.allocations.serializers import (
    AllocationSerializer,
    AllocationListSerializer,
    AllocationCreateSerializer,
    TransferSerializer,
)


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
        employee = getattr(user, "employee_profile", None)
        if employee:
            return queryset.filter(employee=employee)
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
        """Allocate an asset to an employee. Updates asset status to 'allocated'."""
        data = request.data.copy()
        user = request.user
        user_org = getattr(user, "organization", None)

        # Resolve asset to get its organization (needed for super admins with no own org)
        asset_id = data.get("asset")
        if asset_id:
            from apps.assets.inventory.models import Asset
            try:
                asset_obj = Asset.objects.select_related("organization").get(pk=asset_id)
                alloc_org = user_org or asset_obj.organization
            except Asset.DoesNotExist:
                alloc_org = user_org
        else:
            alloc_org = user_org

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

        return success_response(
            data=AllocationSerializer(allocation).data,
            message="Asset allocated successfully.",
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
        # is_current checks returned_at — not the BaseModel soft-delete flag
        if instance.is_current:
            asset = instance.asset
            update_fields = ["status", "updated_at"]
            if hasattr(asset, "updated_by"):
                asset.updated_by = request.user
                update_fields.append("updated_by")
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
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return success_response(
                data=self.get_paginated_response(serializer.data).data
            )
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)

    @action(detail=True, methods=["post"], url_path="transfer")
    def transfer(self, request, alloc_id=None):
        """
        Transfer an asset from its current holder to a different employee.

        Closes the current allocation (sets returned_at) and creates a new
        active allocation for the new employee. The asset status remains 'allocated'.
        """
        current_allocation = self.get_object()

        if not current_allocation.is_current:
            return Response(
                {"error": "This allocation is already returned."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_employee = serializer.validated_data["employee"]
        transfer_notes = serializer.validated_data.get("notes", "")

        # Cross-org guard — target employee must be in the same org as the allocation
        if new_employee.organization != current_allocation.organization:
            return Response(
                {"error": "Cannot transfer to an employee of a different organization."},
                status=status.HTTP_400_BAD_REQUEST,
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
            return Response(
                {"error": "This asset has already been returned."},
                status=status.HTTP_400_BAD_REQUEST,
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

        return success_response(
            data=AllocationSerializer(instance).data,
            message="Asset returned successfully.",
        )
