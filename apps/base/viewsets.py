"""
apps/base/viewsets.py — Base ViewSet and BulkOperationsMixin.

BaseViewSet provides role-based data scoping (super admin → all, org admin → org, employee → limited).
BulkOperationsMixin provides bulk create/update/delete actions.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.base.enums import UserRole


@extend_schema_view(
    list=extend_schema(description='List all accessible records.'),
    retrieve=extend_schema(description='Retrieve a single record.'),
    create=extend_schema(description='Create a new record.'),
    update=extend_schema(description='Update a record.'),
    partial_update=extend_schema(description='Partially update a record.'),
    destroy=extend_schema(description='Soft delete a record.'),
)
class BaseViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet with role-based data scoping.

    - Super admin: sees all data across all organizations
    - Org admin: sees their organization's data
    - Employee: sees limited data (controlled by scope_for_employee)

    Child ViewSets override scope_queryset() and scope_for_employee().
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

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
        if getattr(user, 'role', None) == UserRole.SUPER_ADMIN.value:
            return queryset

        # Filter by organization if the model has an organization field
        if hasattr(model, 'organization'):
            user_org = getattr(user, 'organization', None)
            if user_org:
                queryset = queryset.filter(organization=user_org)

        # Employee: apply additional restrictions
        if getattr(user, 'role', None) == UserRole.EMPLOYEE.value:
            queryset = self.scope_for_employee(queryset)

        return queryset

    def scope_for_employee(self, queryset):
        """
        Override in subclasses to restrict employee access.

        Default implementation returns the queryset unchanged (employee sees all org data).
        Common overrides:
            - Employee sees only assigned assets: queryset.filter(allocated_to=employee)
            - Employee sees only own requests: queryset.filter(requested_by=employee)
        """
        return queryset

    def perform_create(self, serializer):
        """Set created_by on create."""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """Set updated_by on update."""
        serializer.save(updated_by=self.request.user)


class BulkOperationsMixin(viewsets.GenericViewSet):
    """
    Self-sufficient mixin providing bulk-create, bulk-update, and bulk-delete actions.

    Inherits from GenericViewSet so it can stand alone or be mixed into any ViewSet.

    - POST /bulk-create/ — Create multiple records
    - PUT /bulk-update/ — Update multiple records (by id)
    - DELETE /bulk-delete/ — Soft-delete multiple records (by id)
    """

    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Create multiple records in a single request."""
        from apps.base.services import BulkService
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

    @action(detail=False, methods=['put'], url_path='bulk-update')
    def bulk_update(self, request):
        """Update multiple records in a single request."""
        from apps.base.services import BulkService
        updates = request.data if isinstance(request.data, list) else request.data.get('items', [])
        updated_count = BulkService.bulk_update(
            queryset=self.get_queryset(),
            updates=updates,
            user=request.user,
        )
        return Response({'updated': updated_count})

    @action(detail=False, methods=['delete'], url_path='bulk-delete')
    def bulk_delete(self, request):
        """Soft-delete multiple records in a single request."""
        from apps.base.services import BulkService
        ids = request.data.get('ids', []) if isinstance(request.data, dict) else request.data
        queryset = self.get_queryset().filter(id__in=ids)
        count = BulkService.bulk_soft_delete(queryset)
        return Response({'deleted': count})