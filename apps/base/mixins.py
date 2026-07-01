"""
apps/base/mixins.py — Reusable mixins for views, serializers, and ViewSets.

Provides:
- OrganizationScopedMixin: Org resolution for multi-tenant views
- ScopeQuerysetMixin: Role-based queryset scoping for ViewSets
- ValidateSameOrgMixin: Cross-org validation
- AuditActionMixin: Auto-set created_by/updated_by with logging
- PaginatedResponseMixin: Standardized paginated response helper
- StatusWorkflowMixin: Status transition validation
"""

import logging

from rest_framework import status
from rest_framework.response import Response

from apps.base.response import error_response, success_response

logger = logging.getLogger(__name__)


# ==============================================================================
# Organization Scoping
# ==============================================================================


class OrganizationScopedMixin:
    """Provides org-scoping logic for API views.

    Super admins can query any org via ``?organization_id=``;
    regular users are scoped to their own org.

    Usage:
        class MyView(OrganizationScopedMixin, APIView):
            def get(self, request):
                org, error = self.get_organization_or_error(request)
                if error:
                    return error
                # ... use org
    """

    def resolve_organization(self, request):
        """Return the organization scoped to this request."""
        user = request.user
        is_super_admin = getattr(user, "role", None) == "super_admin"

        if is_super_admin:
            org_id = request.query_params.get("organization_id")
            if org_id:
                return org_id
        return user.organization

    def get_organization_or_error(self, request):
        """Return (org, None) or (None, error_response)."""
        org = self.resolve_organization(request)
        if org is None:
            return None, error_response(
                message="User has no organization assigned.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return org, None


# ==============================================================================
# ViewSet: Queryset Scoping
# ==============================================================================


class ScopeQuerysetMixin:
    """Role-based queryset scoping for ViewSets.

    - Super admin: sees all data across all organizations
    - Org admin: sees their organization's data
    - Employee: sees limited data (controlled by scope_for_employee)

    Usage:
        class MyViewSet(ScopeQuerysetMixin, viewsets.ModelViewSet):
            def scope_for_employee(self, queryset):
                return queryset.filter(assigned_to=self.request.user.employee)
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        return self.scope_queryset(queryset)

    def scope_queryset(self, queryset):
        """Apply role-based filtering to the queryset."""
        user = self.request.user
        model = queryset.model

        if getattr(user, "is_super_admin", False):
            return queryset

        if hasattr(model, "organization"):
            user_org = getattr(user, "organization", None)
            if user_org:
                queryset = queryset.filter(organization=user_org)

        if getattr(user, "is_employee", False):
            queryset = self.scope_for_employee(queryset)

        return queryset

    def scope_for_employee(self, queryset):
        """Override in subclasses to restrict employee access.

        Common overrides:
            - Employee sees only assigned assets: queryset.filter(allocated_to=employee)
            - Employee sees only own requests: queryset.filter(requested_by=employee)
        """
        return queryset


# ==============================================================================
# ViewSet: Cross-Org Validation
# ==============================================================================


class ValidateSameOrgMixin:
    """Validates that related objects belong to the same organization.

    Use in custom actions that accept foreign objects (e.g., assign, transfer).
    """

    def validate_same_org(self, instance, related_obj, field_name="related object"):
        """Return an error Response if orgs don't match, or None if valid."""
        instance_org = getattr(instance, "organization", None)
        related_org = getattr(related_obj, "organization", None)
        if instance_org and related_org and instance_org.id != related_org.id:
            return Response(
                {"error": f"This {field_name} does not belong to your organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None


# ==============================================================================
# ViewSet: Audit Logging (created_by / updated_by)
# ==============================================================================


class AuditActionMixin:
    """Auto-sets created_by / updated_by on model saves and logs actions.

    Mix into any ViewSet whose model has created_by / updated_by fields.
    """

    def perform_create(self, serializer):
        """Set created_by on create if the model supports it."""
        kwargs = {}
        if hasattr(serializer.Meta.model, "created_by"):
            kwargs["created_by"] = self.request.user
        serializer.save(**kwargs)
        logger.info(
            "Created %s by %s",
            serializer.Meta.model.__name__,
            self.request.user.email if self.request.user.is_authenticated else "anonymous",
        )

    def perform_update(self, serializer):
        """Set updated_by on update if the model supports it."""
        kwargs = {}
        if hasattr(serializer.Meta.model, "updated_by"):
            kwargs["updated_by"] = self.request.user
        serializer.save(**kwargs)
        logger.info(
            "Updated %s pk=%s by %s",
            serializer.Meta.model.__name__,
            serializer.instance.pk,
            self.request.user.email if self.request.user.is_authenticated else "anonymous",
        )

    def perform_destroy(self, instance):
        """Soft-delete via BaseModel.delete(). Returns 204 No Content."""
        model_name = instance.__class__.__name__
        instance.delete()
        logger.info(
            "Soft-deleted %s pk=%s by %s",
            model_name,
            instance.pk,
            self.request.user.email if self.request.user.is_authenticated else "anonymous",
        )


# ==============================================================================
# ViewSet: Paginated Response
# ==============================================================================


class PaginatedResponseMixin:
    """Provides paginated_response() for custom ViewSet actions."""

    def paginated_response(self, queryset, serializer_class):
        """
        Paginate a queryset and return a standardized response.

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


# ==============================================================================
# ViewSet: Status Workflow Validation
# ==============================================================================


class StatusWorkflowMixin:
    """Validates status transitions in workflow actions.

    Example:
        class IncidentViewSet(StatusWorkflowMixin, ...):
            @action(detail=True, methods=['post'])
            def resolve(self, request, pk=None):
                err = self.require_status(instance, 'in_progress', 'resolved')
                if err:
                    return err
    """

    def require_status(self, instance, expected_status, action_name=None):
        """
        Validate that an instance has the expected status before a workflow action.

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
