"""
apps/assets/requests/views.py — ViewSets for AssetRequest.
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.base.constants import UserRole, RequestStatus
from apps.base.permissions import RoleBasedPermission
from apps.base.response import success_response
from apps.base.viewsets import BaseViewSet
from apps.assets.categories.models import AssetCategory
from apps.assets.requests.filters import AssetRequestFilterSet
from apps.assets.requests.models import AssetRequest
from apps.assets.requests.permissions import IsRequesterOrManagerOrAdmin, IsManagerOrAdmin
from apps.assets.requests.serializers import (
    AssetRequestSerializer,
    AssetRequestListSerializer,
    AssetRequestCreateSerializer,
    ApproveRejectSerializer,
)


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
        employee = getattr(user, "employee_profile", None)
        if employee:
            return queryset.filter(requested_by=employee)
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
        """Create a new asset request. Internal admin/submit endpoint."""
        return self._submit(request)

    @action(detail=False, methods=["post"], url_path="submit")
    def submit(self, request):
        """
        Submit a new asset request (employee-facing action).

        Sets `requested_by` to the current user's employee profile and
        `organization` to their organization.
        """
        return self._submit(request)

    def _submit(self, request):
        """Shared create logic for both create and submit actions."""
        data = request.data.copy()
        user = request.user
        user_org = getattr(user, "organization", None)

        # Resolve category to get its organization for super admin path
        category_id = data.get("asset_category")
        if category_id and user_org is None:
            

            try:
                cat_obj = AssetCategory.objects.select_related("organization").get(
                    pk=category_id
                )
                submit_org = cat_obj.organization
            except AssetCategory.DoesNotExist:
                submit_org = None
        else:
            submit_org = user_org

        # Inject requested_by from the current user's employee profile
        employee = getattr(user, "employee_profile", None)
        if not employee:
            return Response(
                {"error": "No employee profile found for the current user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            organization=submit_org,
            requested_by=employee,
            status=RequestStatus.PENDING.value,
        )

        return success_response(
            data=AssetRequestSerializer(serializer.instance).data,
            message="Asset request submitted successfully.",
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

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, req_id=None):
        """
        Approve a pending asset request.

        Sets status to 'approved' and records the reviewer.
        """
        instance = self.get_object()

        if instance.status != RequestStatus.PENDING.value:
            return Response(
                {"error": "Only pending requests can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ApproveRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        now = timezone.now()
        instance.status = RequestStatus.APPROVED.value
        instance.reviewed_by = request.user
        instance.reviewed_at = now
        instance.review_notes = serializer.validated_data.get("review_notes", "")
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

        return success_response(
            data=AssetRequestSerializer(instance).data,
            message="Asset request approved.",
        )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, req_id=None):
        """
        Reject a pending asset request.

        Sets status to 'rejected' and records the reviewer and notes.
        """
        instance = self.get_object()

        if instance.status != RequestStatus.PENDING.value:
            return Response(
                {"error": "Only pending requests can be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ApproveRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        now = timezone.now()
        instance.status = RequestStatus.REJECTED.value
        instance.reviewed_by = request.user
        instance.reviewed_at = now
        instance.review_notes = serializer.validated_data.get("review_notes", "")
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

        return success_response(
            data=AssetRequestSerializer(instance).data,
            message="Asset request rejected.",
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
        employee = getattr(user, "employee_profile", None)

        # Only the requester (not their manager) can cancel via this action.
        # Managers use soft-delete (destroy) instead.
        if employee and instance.requested_by_id != employee.id:
            return Response(
                {"error": "You can only cancel your own requests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if instance.status != RequestStatus.PENDING.value:
            return Response(
                {"error": "Only pending requests can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.delete()  # soft-delete
        return Response(status=status.HTTP_204_NO_CONTENT)
