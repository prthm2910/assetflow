"""
apps/assets/inventory/views.py — ViewSets for Asset.
"""

import logging

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
from apps.assets.inventory.services import AssetService

logger = logging.getLogger(__name__)


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

    def create(self, request, *args, **kwargs):
        # Inject organization based on user role, then validate via serializer
        data = request.data.copy()
        AssetService.inject_organization(request.user, data)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        asset = serializer.save()
        logger.info("Asset created: %s (%s) by %s", asset.name, asset.asset_id, request.user.email)
        return success_response(
            data=serializer.data,
            message="Asset created successfully.",
            status_code=status.HTTP_201_CREATED,
        )

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
        asset = AssetService.change_status(
            instance, serializer.validated_data["status"], request.user
        )
        logger.info(
            "Asset %s status changed to %s by %s",
            asset.asset_id,
            asset.status,
            request.user.email,
        )
        return success_response(
            data=AssetSerializer(asset, context=self.get_serializer_context()).data,
            message=f"Asset status changed to {asset.status}.",
        )
