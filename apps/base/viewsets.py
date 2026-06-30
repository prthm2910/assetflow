"""
apps/base/viewsets.py — Base ViewSet and BulkOperationsMixin.

BaseViewSet provides role-based data scoping (super admin → all, org admin → org, employee → limited).
StandardResponseMixin auto-wrapes DRF responses in the {success, data} envelope.
BulkOperationsMixin provides bulk create/update/delete actions.
"""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.base.permissions import RoleBasedPermission
from apps.base.services import BulkService
from apps.base.response import StandardResponseMixin, success_response, error_response


# ==============================================================================
# Base ViewSet
# ==============================================================================


@extend_schema_view(
    list=extend_schema(description="List all accessible records."),
    retrieve=extend_schema(description="Retrieve a single record."),
    create=extend_schema(description="Create a new record."),
    update=extend_schema(description="Update a record."),
    partial_update=extend_schema(description="Partially update a record."),
    destroy=extend_schema(description="Soft delete a record."),
)
class BaseViewSet(StandardResponseMixin, viewsets.ModelViewSet):
    """
    Base ViewSet with role-based data scoping and permission controls.

    - Super admin: sees all data across all organizations
    - Org admin: sees their organization's data
    - Employee: sees limited data (controlled by scope_for_employee)

    Permissions via get_permissions() / RoleBasedPermission:
        - Override read_roles / write_roles class attributes to restrict access.
        - Empty (default) = all authenticated users can perform that operation.

    Data scoping via scope_queryset() / scope_for_employee():
        - Override these to control what data each role can access.
    """

    # Override these in subclasses with UserRole enum members
    read_roles: list = []
    write_roles: list = []

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_permissions(self) -> list[BasePermission]:
        perms: list[BasePermission] = [IsAuthenticated()]
        if self.read_roles or self.write_roles:
            perms.append(RoleBasedPermission(
                read_roles=self.read_roles,
                write_roles=self.write_roles,
            ))
        return perms

    def get_queryset(self):
        queryset = super().get_queryset()
        return self.scope_queryset(queryset)

    def scope_queryset(self, queryset):
        """
        Apply role-based filtering to the queryset.

        - Super admin: sees everything
        - Org admin: sees their organization's data
        - Employee: uses scope_for_employee for further restriction
        """
        user = self.request.user
        model = queryset.model

        # Super admin sees everything
        if user.is_super_admin:
            return queryset

        # Filter by organization if the model has an organization field
        if hasattr(model, "organization"):
            user_org = getattr(user, "organization", None)
            if user_org:
                queryset = queryset.filter(organization=user_org)

        # Employee: apply additional restrictions
        if user.is_employee:
            queryset = self.scope_for_employee(queryset)

        return queryset

    def scope_for_employee(self, queryset):
        """
        Override in subclasses to restrict employee access.

        Default implementation returns the queryset unchanged.
        Common overrides:
            - Employee sees only assigned assets: queryset.filter(allocated_to=employee)
            - Employee sees only own requests: queryset.filter(requested_by=employee)
        """
        return queryset

    def validate_same_org(self, instance, related_obj, field_name="related object"):
        """
        Validate that a related object belongs to the same organization as the instance.

        Returns an error Response if orgs don't match, or None if valid.
        Use in custom actions that accept foreign objects (e.g., assign, transfer).

        Example:
            err = self.validate_same_org(incident, employee, "employee")
            if err:
                return err
        """
        instance_org = getattr(instance, "organization", None)
        related_org = getattr(related_obj, "organization", None)
        if instance_org and related_org and instance_org.id != related_org.id:
            return Response(
                {"error": f"This {field_name} does not belong to your organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def perform_create(self, serializer):
        """Set created_by on create if the model supports it."""
        kwargs = {}
        if hasattr(serializer.Meta.model, "created_by"):
            kwargs["created_by"] = self.request.user
        serializer.save(**kwargs)

    def perform_update(self, serializer):
        """Set updated_by on update if the model supports it."""
        kwargs = {}
        if hasattr(serializer.Meta.model, "updated_by"):
            kwargs["updated_by"] = self.request.user
        serializer.save(**kwargs)

    def perform_destroy(self, instance):
        """Soft-delete via BaseModel.delete(). Returns 204 No Content."""
        instance.delete()  # BaseModel.delete() → soft-delete

    def paginated_response(self, queryset, serializer_class):
        """
        Paginate a queryset and return a standardized response.

        Replaces the repetitive 5-line pagination pattern in custom actions.

        Args:
            queryset: The Django QuerySet to paginate.
            serializer_class: The serializer class to use.

        Returns:
            Response with paginated or full data wrapped in success_response.
        """
        page = self.paginate_queryset(queryset)
        serializer = serializer_class(page if page is not None else queryset, many=True)
        if page is not None:
            return success_response(data=self.get_paginated_response(serializer.data).data)
        return success_response(data=serializer.data)

    def require_status(self, instance, expected_status, action_name=None):
        """
        Validate that an instance has the expected status before a workflow action.

        Returns an error Response if status doesn't match, or None if valid.

        Example:
            err = self.require_status(instance, "pending", "approve")
            if err:
                return err

        Args:
            instance: The model instance to check.
            expected_status: The required status value.
            action_name: Optional action verb for the error message.

        Returns:
            Response on failure, None on success.
        """

        if instance.status != expected_status:
            verb = f" {action_name}" if action_name else ""
            return error_response(
                message=(
                    f"Only records with status '{expected_status}' can be{verb}. "
                    f"Current status: '{instance.status}'."
                ),
                code="INVALID_STATUS",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return None


class BulkOperationsMixin(viewsets.GenericViewSet):
    """
    Self-sufficient mixin providing bulk-create, bulk-update, and bulk-delete actions.

    Inherits from GenericViewSet so it can stand alone or be mixed into any ViewSet.

    - POST /bulk-create/ — Create multiple records
    - PUT /bulk-update/ — Update multiple records (by id)
    - DELETE /bulk-delete/ — Soft-delete multiple records (by id)
    """

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        """Create multiple records in a single request."""
        

        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        instances = BulkService.bulk_create(
            serializer_class=self.get_serializer_class(),
            validated_data=serializer.validated_data,
            context=self.get_serializer_context(),
        )
        return Response(
            self.get_serializer(instances, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["put"], url_path="bulk-update")
    def bulk_update(self, request):
        """Update multiple records in a single request. Client sends HRIDs."""
        from apps.base.services import BulkService

        updates = (
            request.data
            if isinstance(request.data, list)
            else request.data.get("items", [])
        )
        hrid_field = self.lookup_field
        hrids = [item.get("id") for item in updates if item.get("id")]
        queryset = self.get_queryset().filter(**{f"{hrid_field}__in": hrids})

        # Map HRIDs to UUIDs for BulkService
        hrid_to_uuid = {getattr(obj, hrid_field): obj.id for obj in queryset}
        for item in updates:
            if "id" in item and item["id"] in hrid_to_uuid:
                item["id"] = hrid_to_uuid[item["id"]]

        updated_count = BulkService.bulk_update(
            queryset=queryset,
            updates=updates,
            user=request.user,
        )
        return Response({"updated": updated_count})

    @action(detail=False, methods=["delete"], url_path="bulk-delete")
    def bulk_delete(self, request):
        """Soft-delete multiple records in a single request. Client sends HRIDs."""

        ids = (
            request.data.get("ids", [])
            if isinstance(request.data, dict)
            else request.data
        )
        hrid_field = self.lookup_field
        queryset = self.get_queryset().filter(**{f"{hrid_field}__in": ids})
        count = BulkService.bulk_soft_delete(queryset)
        return Response({"deleted": count})
