"""
apps/assets/inventory/views.py — ViewSets for Asset.
"""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.base.constants import UserRole
from apps.base.response import success_response
from apps.base.viewsets import BaseViewSet
from apps.assets.inventory.filters import AssetFilterSet
from apps.assets.inventory.models import Asset
from apps.assets.inventory.serializers import (
    AssetListSerializer,
    AssetSerializer,
    AssetStatusChangeSerializer,
)


class AssetViewSet(BaseViewSet):
    """
    Asset inventory management within an organization.

    - Super admin: full CRUD across all organizations
    - Org admin: full CRUD within their organization
    - Employee: read-only within their organization

    Custom actions:
        - change_status: Update asset lifecycle status

    Permissions:
        - Read (GET): Any authenticated user in the org
        - Write (POST/PUT/PATCH/DELETE): Org admin + Super admin
    """

    lookup_field = "asset_id"
    lookup_value_regex = r"[\w-]+"
    ordering_fields = ["name", "created_at", "status", "asset_id"]
    ordering = ["-created_at"]
    search_fields = ["name", "brand", "serial_number", "asset_id"]

    filterset_class = AssetFilterSet
    write_roles = [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]

    def get_queryset(self):
        """Select related fields and apply role-based scoping."""
        queryset = Asset.objects.select_related(
            "organization", "category", "assigned_to", "assigned_to__user"
        )
        return self.scope_queryset(queryset)

    def get_serializer_class(self):
        if self.action == "list":
            return AssetListSerializer
        return AssetSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return success_response(
                data=self.get_paginated_response(serializer.data).data
            )
        serializer = AssetListSerializer(queryset, many=True)
        return success_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(data=serializer.data)

    def create(self, request, *args, **kwargs):
        # Auto-fill organization from user context if not provided
        data = request.data.copy()
        user = request.user
        user_org = getattr(user, "organization", None)
        if user_org and "organization" not in data:
            data["organization"] = str(user_org.id)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message="Asset created successfully.",
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

    @action(detail=True, methods=["patch"], url_path="change-status")
    def change_status(self, request, asset_id=None):
        """
        Change an asset's lifecycle status.

        Status values are defined in AssetStatus (procured, available,
        allocated, maintenance, retired). Full lifecycle transitions are
        enforced by the allocations module (Module 7).
        """
        instance = self.get_object()
        serializer = AssetStatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance.status = serializer.validated_data["status"]
        instance.save(update_fields=["status", "updated_at"])
        return success_response(
            data=AssetSerializer(instance).data,
            message=f"Asset status changed to {instance.status}.",
        )
