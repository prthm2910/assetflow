"""
apps/assets/categories/views.py — ViewSets for AssetCategory.
"""

from collections import defaultdict

from django.db.models import Count, Q

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.base.constants import UserRole
from apps.base.response import success_response
from apps.base.viewsets import BaseViewSet, BulkOperationsMixin
from apps.assets.categories.models import AssetCategory
from apps.assets.categories.serializers import (
    AssetCategoryListSerializer,
    AssetCategorySerializer,
    AssetCategoryTreeSerializer,
)


class AssetCategoryViewSet(BaseViewSet, BulkOperationsMixin):
    """
    Asset Category management within an organization.

    - Super admin: full CRUD across all organizations
    - Org admin: full CRUD within their organization
    - Employee: read-only within their organization

    Custom actions:
        - tree: Returns full category hierarchy as nested tree (N+1-free)
        - descendants: Returns flat list of all descendant categories (N+1-free)

    Permissions:
        - Read (GET): Any authenticated user in the org
        - Write (POST/PUT/PATCH/DELETE): Org admin + Super admin
    """

    lookup_field = "cat_id"
    lookup_value_regex = r"[\w]+"
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    write_roles = [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]

    def get_queryset(self):
        """Annotate sub_category_count to avoid N+1 queries in list views."""
        queryset = (
            AssetCategory.objects.select_related("parent", "organization")
            .annotate(
                sub_category_count_annotated=Count(
                    "sub_categories",
                    filter=Q(
                        sub_categories__is_deleted=False,
                        sub_categories__is_active=True,
                    ),
                )
            )
        )
        return self.scope_queryset(queryset)

    def get_serializer_class(self):
        if self.action == "list":
            return AssetCategoryListSerializer
        if self.action == "tree":
            return AssetCategoryTreeSerializer
        return AssetCategorySerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return success_response(
                data=self.get_paginated_response(serializer.data).data
            )
        serializer = AssetCategoryListSerializer(queryset, many=True)
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
            message="Asset category created successfully.",
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

    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request):
        """
        Returns the full category hierarchy as a nested tree.
        Uses a single query + parent_map for N+1-free rendering.
        """
        # Build parent_map in one query — avoids N+1 on recursive serialization
        filters = {"is_deleted": False, "is_active": True}
        if getattr(request.user, "role", None) != UserRole.SUPER_ADMIN.value:
            user_org = getattr(request.user, "organization", None)
            if user_org:
                filters["organization"] = user_org

        all_categories = AssetCategory.objects.filter(**filters)
        parent_map = defaultdict(list)
        for cat in all_categories:
            parent_pk = cat.parent.id if cat.parent else None
            if parent_pk:
                parent_map[parent_pk].append(cat)

        context = self.get_serializer_context()
        context["parent_map"] = parent_map

        queryset = self.get_queryset().filter(parent__isnull=True).order_by("name")
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AssetCategoryTreeSerializer(
                page, many=True, context=context
            )
            return success_response(
                data=self.get_paginated_response(serializer.data).data
            )
        serializer = AssetCategoryTreeSerializer(
            queryset, many=True, context=context
        )
        return success_response(data=serializer.data)

    @action(detail=True, methods=["get"], url_path="descendants")
    def descendants(self, request, cat_id=None):
        """Returns all descendant categories using single-query in-memory collection."""
        instance = self.get_object()
        descendants = self._collect_descendants(instance)
        serializer = AssetCategoryListSerializer(descendants, many=True)
        return success_response(
            data=serializer.data,
            message=f"Found {len(descendants)} descendant categories.",
        )

    def _collect_descendants(self, category):
        """
        Collect all descendants using a single DB query + in-memory tree traversal.
        Avoids N+1 on deep hierarchies.
        """
        # Single query: fetch all active non-deleted categories in the org
        all_categories = list(
            AssetCategory.objects.filter(
                organization_id=category.organization_id,
                is_deleted=False,
                is_active=True,
            ).order_by("name")
        )

        # Build adjacency map: parent_id -> [children]
        children_map = defaultdict(list)
        for cat in all_categories:
            parent_pk = cat.parent.id if cat.parent else None
            if parent_pk:
                children_map[parent_pk].append(cat)

        # Collect descendants in-memory
        result = []

        def collect(parent_id):
            for child in children_map[parent_id]:
                result.append(child)
                collect(child.id)

        collect(category.id)
        return result
