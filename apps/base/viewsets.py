"""
apps/base/viewsets.py — Base ViewSet.

BaseViewSet assembles reusable mixins from apps.base.mixins into the standard
ViewSet used across all modules. Also provides BaseOrgAPIView and
BaseOrgTemplateView for non-ViewSet (APIView) patterns.
"""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.base.mixins import (
    AuditActionMixin,
    OrganizationScopedMixin,
    PaginatedResponseMixin,
    ScopeQuerysetMixin,
    StatusWorkflowMixin,
    ValidateSameOrgMixin,
)
from apps.base.permissions import RoleBasedPermission
from apps.base.response import StandardResponseMixin, success_response


# ==============================================================================
# Base ViewSet — assembles mixins into one canonical ViewSet
# ==============================================================================


@extend_schema_view(
    list=extend_schema(description="List all accessible records."),
    retrieve=extend_schema(description="Retrieve a single record."),
    create=extend_schema(description="Create a new record."),
    update=extend_schema(description="Update a record."),
    partial_update=extend_schema(description="Partially update a record."),
    destroy=extend_schema(description="Soft delete a record."),
)
class BaseViewSet(
    StandardResponseMixin,
    ScopeQuerysetMixin,
    AuditActionMixin,
    ValidateSameOrgMixin,
    PaginatedResponseMixin,
    StatusWorkflowMixin,
    viewsets.ModelViewSet,
):
    """
    Base ViewSet with role-based data scoping and permission controls.

    Inherits from reusable mixins (in order of resolution):
    - StandardResponseMixin — auto-wraps DRF responses in {success, data}
    - ScopeQuerysetMixin — role-based org scoping (super admin / org admin / employee)
    - AuditActionMixin — auto-sets created_by/updated_by with logging
    - ValidateSameOrgMixin — cross-organization validation for related objects
    - PaginatedResponseMixin — paginated_response() helper for custom actions
    - StatusWorkflowMixin — require_status() for workflow transitions
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


# ==============================================================================
# Base API & Template Views (Org-scoped, non-ViewSet)
# ==============================================================================


class BaseOrgAPIView(OrganizationScopedMixin, APIView):
    """Authenticated, org-scoped JSON API view.

    Handles auth, org resolution, null-org error, and standardized response wrapping.

    Subclasses override ``get_data(org)`` and optionally ``get_message()``.
    """

    permission_classes = [IsAuthenticated]

    def get_data(self, org):
        """Override in subclasses — return the response data dict."""
        raise NotImplementedError

    def get_message(self):
        """Override to customize the success message."""
        return "Data retrieved successfully."

    def get(self, request, *args, **kwargs):
        org, error = self.get_organization_or_error(request)
        if error:
            return error
        return success_response(data=self.get_data(org), message=self.get_message())


class BaseOrgTemplateView(OrganizationScopedMixin, APIView):
    """Authenticated, org-scoped HTML template view using DRF's TemplateHTMLRenderer.

    Subclasses set ``template_name`` and override ``get_context_data(org)``.
    """

    permission_classes = [IsAuthenticated]
    renderer_classes = [TemplateHTMLRenderer]
    template_name = None

    def get_context_data(self, org):
        """Override in subclass — return extra template context."""
        return {}

    def get(self, request, *args, **kwargs):
        org, error = self.get_organization_or_error(request)
        ctx = {"organization_name": str(org) if org else "—"}
        if org:
            ctx.update(self.get_context_data(org))
        status_code = error.status_code if error else status.HTTP_200_OK
        return Response(template_name=self.template_name, data=ctx, status=status_code)
