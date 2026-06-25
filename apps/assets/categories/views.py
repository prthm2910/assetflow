"""
apps/assets/categories/views.py — ViewSets for AssetCategory.
"""

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
        - tree: Returns full category hierarchy as nested tree
        - descendants: Returns flat list of all descendant categories

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
        queryset = AssetCategory.objects.select_related("parent", "organization")
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
        Only top-level categories (parent=null) are returned as roots.
        """
        queryset = self.get_queryset().filter(parent__isnull=True)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return success_response(
                data=self.get_paginated_response(serializer.data).data
            )
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)

    @action(detail=True, methods=["get"], url_path="descendants")
    def descendants(self, request, cat_id=None):
        """Returns all descendant categories (children, grandchildren, etc.) as flat list."""
        instance = self.get_object()
        descendants = self._collect_descendants(instance)
        serializer = AssetCategoryListSerializer(descendants, many=True)
        return success_response(
            data=serializer.data,
            message=f"Found {len(descendants)} descendant categories.",
        )

    def _collect_descendants(self, category):
        """Recursively collect all descendant categories."""
        result = []
        children = list(
            category.sub_categories.filter(is_deleted=False, is_active=True)
        )
        for child in children:
            result.append(child)
            result.extend(self._collect_descendants(child))
        return result
