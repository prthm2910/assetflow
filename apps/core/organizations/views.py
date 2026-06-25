"""
apps/core/organizations/views.py — ViewSets for Organization and OrganizationProfile.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.base.constants import UserRole
from apps.base.response import error_response, success_response
from apps.base.viewsets import BaseViewSet, BulkOperationsMixin
from apps.core.organizations.models import Organization, OrganizationConfig
from apps.core.organizations.serializers import (
    OrganizationConfigSerializer,
    OrganizationListSerializer,
    OrganizationProfileSerializer,
    OrganizationSerializer,
)


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
class OrganizationViewSet(BaseViewSet, BulkOperationsMixin):
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
        if getattr(user, "role", None) == UserRole.SUPER_ADMIN.value:
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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message="Organization created successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
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

    @extend_schema(
        tags=["Organizations"],
        summary="Toggle organization active status",
        description="Activate or deactivate an organization. Super admin only.",
    )
    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, org_id=None):
        """Toggle is_active on an organization."""
        # Check write permission for this action
        if getattr(request.user, "role", None) != UserRole.SUPER_ADMIN.value:
            return error_response(
                message="Only super admins can toggle organization status.",
                code="FORBIDDEN",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        instance = self.get_object()
        instance.is_active = not instance.is_active
        instance.save(update_fields=["is_active", "updated_at"])
        serializer = OrganizationSerializer(instance)
        return success_response(
            data=serializer.data,
            message=f"Organization {'activated' if instance.is_active else 'deactivated'}.",
        )

    @extend_schema(
        tags=["Organizations"],
        summary="Get organization config",
        description="Retrieve organization config. Org admin/employee see own org config.",
    )
    @action(detail=True, methods=["get", "patch"], url_path="config")
    def config(self, request, org_id=None):  # noqa: ARG001 (org_id from URL pattern)
        """GET or PATCH the config for an organization."""
        instance = self.get_object()
        try:
            config = instance.config
        except OrganizationConfig.DoesNotExist:
            return error_response(
                message="Organization config not found.",
                code="CONFIG_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if request.method == "GET":
            serializer = OrganizationConfigSerializer(config)
            return success_response(data=serializer.data)

        # PATCH — super admin only
        if getattr(request.user, "role", None) != UserRole.SUPER_ADMIN.value:
            return error_response(
                message="Only super admins can update organization config.",
                code="FORBIDDEN",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = OrganizationConfigSerializer(
            config,
            data=request.data,
            partial=True,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
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

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return error_response(
                message="No organization assigned to your account.",
                code="ORG_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(instance)
        return success_response(data=serializer.data)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return error_response(
                message="No organization assigned to your account.",
                code="ORG_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data)
