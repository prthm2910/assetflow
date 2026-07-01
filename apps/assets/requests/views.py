"""
apps/assets/requests/views.py — ViewSets for AssetRequest.
"""

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.base.constants import UserRole
from apps.assets.requests.constants import RequestStatus
from apps.base.permissions import RoleBasedPermission
from apps.base.response import success_response, error_response
from apps.base.viewsets import BaseViewSet
from apps.assets.requests.filters import AssetRequestFilterSet
from apps.assets.requests.models import AssetRequest
from apps.assets.requests.permissions import IsRequesterOrManagerOrAdmin, IsManagerOrAdmin
from apps.assets.requests.serializers import (
    AssetRequestSerializer,
    AssetRequestListSerializer,
    AssetRequestCreateSerializer,
    ApproveRejectSerializer,
)
from apps.assets.requests.services import AssetRequestService

logger = logging.getLogger(__name__)


class AssetRequestViewSet(BaseViewSet):
    """
    Asset request management within an organization.

    - Super admin: full CRUD across all organizations
    - Org admin: full CRUD within their organization
    - Employee: read-only (their own requests); submit; cancel their own requests

    Org isolation is enforced at the queryset level by scope_queryset().
    Custom action permissions are defined in get_permissions().

    Custom actions:
        - submit: any authenticated user in their org
        - approve: manager of requester, org admin, or super admin
        - reject:  manager of requester, org admin, or super admin
        - cancel:  requester, their manager, org admin, or super admin
    """

    lookup_field = "req_id"
    lookup_value_regex = r"[\w-]+"
    ordering_fields = [
        "created_at",
        "priority",
        "status",
        "requested_by__user__first_name",
    ]
    ordering = ["-created_at"]
    search_fields = [
        "requested_by__user__first_name",
        "requested_by__user__last_name",
        "asset_category__name",
    ]

    filterset_class = AssetRequestFilterSet

    def get_permissions(self):
        """Action-level permissions — org isolation via scope_queryset."""
        # Standard read: any authenticated user (IsAuthenticated only)
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        # submit: any authenticated user in their org
        if self.action == "submit":
            return [IsAuthenticated()]
        # approve/reject: manager, org admin, or super admin
        if self.action in ("approve", "reject"):
            return [IsManagerOrAdmin()]
        # cancel: requester, their manager, org admin, or super admin
        if self.action == "cancel":
            return [IsRequesterOrManagerOrAdmin()]
        # destroy: org admin + super admin only
        if self.action == "destroy":
            return [RoleBasedPermission(write_roles=[UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN])]
        # Default: same as super() — write_roles enforced (create/update/partial_update)
        return super().get_permissions()

    def get_queryset(self):
        """Select related fields and apply role-based scoping."""
        queryset = AssetRequest.objects.select_related(
            "organization",
            "requested_by",
            "requested_by__user",
            "asset_category",
            "reviewed_by",
        )
        return self.scope_queryset(queryset)

    def get_serializer_class(self):
        if self.action == "list":
            return AssetRequestListSerializer
        if self.action == "create" or self.action == "submit":
            return AssetRequestCreateSerializer
        return AssetRequestSerializer

    def scope_for_employee(self, queryset):
        """Employees see only their own requests."""
        user = self.request.user
        employee = user.employee
        if employee:
            return queryset.filter(requested_by=employee)
        return queryset.none()

    def create(self, request, *args, **kwargs):
        """Create a new asset request — delegates to submit action."""
        return self.submit(request)

    @action(detail=False, methods=["post"], url_path="submit")
    def submit(self, request):
        """
        Submit a new asset request (employee-facing action).

        Sets `requested_by` to the current user's employee profile and
        `organization` to their organization.
        """
        return self._submit(request)

    def _submit(self, request):
        """Shared create logic for both create and submit actions.

        Validates via serializer, then delegates org resolution and
        employee linking to the service layer.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request_obj, error = AssetRequestService.submit(
            request.user, serializer.validated_data
        )
        if error:
            logger.warning("Asset request submit failed by %s: %s", request.user.email, error)
            return error_response(
                message=error,
                code="SUBMIT_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(
            "Asset request submitted: %s by %s",
            request_obj.req_id,
            request.user.email,
        )
        return success_response(
            data=AssetRequestSerializer(
                request_obj, context=self.get_serializer_context()
            ).data,
            message="Asset request submitted successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, req_id=None):
        """Approve a pending asset request."""
        return self._review(
            request, req_id,
            target_status=RequestStatus.APPROVED.value,
            action_verb="approved",
            success_message="Asset request approved.",
        )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, req_id=None):
        """Reject a pending asset request."""
        return self._review(
            request, req_id,
            target_status=RequestStatus.REJECTED.value,
            action_verb="rejected",
            success_message="Asset request rejected.",
        )

    def _review(self, request, req_id, target_status, action_verb, success_message):
        """Shared logic for approve/reject actions."""
        instance = self.get_object()

        err = self.require_status(instance, RequestStatus.PENDING.value, action_verb)
        if err:
            return err

        serializer = ApproveRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        now = timezone.now()
        instance.status = target_status
        instance.reviewed_by = request.user
        instance.reviewed_at = now
        instance.review_notes = serializer.validated_data.get("review_notes", "")
        instance.updated_by = request.user
        instance.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "review_notes",
                "updated_at",
                "updated_by",
            ]
        )

        logger.info(
            "Asset request %s %s by %s",
            req_id,
            action_verb,
            request.user.email,
        )
        return success_response(
            data=AssetRequestSerializer(instance).data,
            message=success_message,
        )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, req_id=None):
        """
        Cancel a pending request.

        Allowed for: requester, their manager, org admin, or super admin.
        Object-level check is handled by IsRequesterOrManagerOrAdmin.
        Additional action-level guard: only the requester (not their manager) can cancel.
        """
        instance = self.get_object()
        user = request.user
        employee = user.employee

        # Only the requester (not their manager) can cancel via this action.
        # Managers use soft-delete (destroy) instead. Admins always pass via permission class.
        if not (user.is_super_admin or user.is_org_admin):
            if employee and instance.requested_by_id != employee.id:
                return error_response(
                    message="You can only cancel your own requests.",
                    code="FORBIDDEN",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        err = self.require_status(instance, RequestStatus.PENDING.value, "cancelled")
        if err:
            return err

        instance.delete()  # soft-delete
        logger.info("Asset request %s cancelled by %s", req_id, request.user.email)
        return Response(status=status.HTTP_204_NO_CONTENT)
