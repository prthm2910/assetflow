"""
apps/core/organizations/views.py — ViewSets for Organization and OrganizationProfile.
"""

import logging

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import action
from apps.base.constants import UserRole
from apps.base.response import success_response
from apps.base.viewsets import BaseViewSet
from apps.core.organizations.models import Organization
from apps.core.organizations.serializers import (
    OrganizationConfigSerializer,
    OrganizationListSerializer,
    OrganizationProfileSerializer,
    OrganizationSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        tags=["Organizations"],
        summary="List organizations",
        description="List all organizations. Super admin sees all; org admin/employee sees own.",
    ),
    retrieve=extend_schema(
        tags=["Organizations"],
        summary="Get organization",
        description="Retrieve a single organization by org_id.",
    ),
    create=extend_schema(
        tags=["Organizations"],
        summary="Create organization",
        description="Create a new organization. Super admin only.",
    ),
    update=extend_schema(
        tags=["Organizations"],
        summary="Update organization",
        description="Full update of an organization. Super admin only.",
    ),
    partial_update=extend_schema(
        tags=["Organizations"],
        summary="Partial update organization",
        description="Partial update of an organization. Super admin only.",
    ),
    destroy=extend_schema(
        tags=["Organizations"],
        summary="Delete organization",
        description="Soft-delete an organization. Super admin only.",
    ),
)
class OrganizationViewSet(BaseViewSet):
    """
    Organization management: CRUD for super admin, read-only for others.

    - Super admin: full CRUD
    - Org admin / Employee: read-only (list/retrieve their own org)

    Permissions:
        - Read (GET): Any authenticated user
        - Write (POST/PUT/PATCH/DELETE): Super admin only
    """

    serializer_class = OrganizationSerializer
    lookup_field = "org_id"
    lookup_value_regex = r"[\w]+"
    ordering_fields = ["name", "created_at"]
    ordering = ["-created_at"]

    # Read: all authenticated (inherited empty list) | Write: super admin only
    write_roles = [UserRole.SUPER_ADMIN]

    def get_queryset(self):
        user = self.request.user

        # Super admin sees all organizations
        if user.is_super_admin:
            return Organization.objects.all()

        # Others see only their own org
        user_org = getattr(user, "organization", None)
        if user_org:
            return Organization.objects.filter(id=user_org.id)
        return Organization.objects.none()

    def get_serializer_class(self):
        if self.action == "list":
            return OrganizationListSerializer
        return OrganizationSerializer

    @extend_schema(
        tags=["Organizations"],
        summary="Get organization config",
        description="Retrieve organization config. Org admin/employee see own org config.",
    )
    @action(detail=True, methods=["get", "patch"], url_path="config")
    def config(self, request, org_id=None):
        """GET or PATCH the config for an organization."""
        instance = self.get_object()
        config = instance.config
        if request.method == "GET":
            serializer = OrganizationConfigSerializer(config)
            return success_response(data=serializer.data)

        serializer = OrganizationConfigSerializer(
            config,
            data=request.data,
            partial=True,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        logger.info("Organization config updated for org %s by %s", org_id, request.user.email)
        return success_response(data=serializer.data)


@extend_schema_view(
    retrieve=extend_schema(
        tags=["Organization Profile"],
        summary="Get own organization profile",
        description="Authenticated user retrieves their own organization profile (including config).",
    ),
    partial_update=extend_schema(
        tags=["Organization Profile"],
        summary="Update own organization profile",
        description="Org admin can update their own organization profile. Employees get read-only.",
    ),
)
class OrganizationProfileViewSet(BaseViewSet):
    """
    Per-user organization profile — authenticated user sees their own org.

    GET /profile/  → own org details
    PATCH /profile/ → update own org profile (org admin only; employees read-only)
    """

    queryset = Organization.objects.all()
    serializer_class = OrganizationProfileSerializer
    http_method_names = ["get", "patch", "options"]  # Only allow GET, PATCH, OPTIONS

    # Read: all authenticated (inherited empty list) | Write: org admin + super admin
    write_roles = [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]

    def get_object(self):
        user = self.request.user
        org = getattr(user, "organization", None)
        if not org:
            return None
        try:
            return Organization.objects.get(id=org.id)
        except Organization.DoesNotExist:
            return None
