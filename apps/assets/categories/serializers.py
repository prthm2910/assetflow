"""
apps/assets/categories/serializers.py — Serializers for AssetCategory.
"""

from rest_framework import serializers

from apps.base.serializers import BaseSerializer
from apps.assets.categories.models import AssetCategory


def _get_active_sub_category_count(obj):
    """Return active sub-category count, using annotation if available."""
    annotated = getattr(obj, "sub_category_count_annotated", None)
    if annotated is not None:
        return annotated
    return obj.sub_categories.active().count()


class AssetCategorySerializer(BaseSerializer):
    """Full serializer for AssetCategory — includes parent name for readability."""

    parent_name = serializers.CharField(
        source="parent.name",
        read_only=True,
        allow_null=True,
    )
    sub_category_count = serializers.SerializerMethodField()

    class Meta:
        model = AssetCategory
        fields = [
            "id",
            "cat_id",
            "name",
            "description",
            "organization",
            "parent",
            "parent_name",
            "sub_category_count",
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]
        read_only_fields = [
            "id",
            "cat_id",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]

    def get_sub_category_count(self, obj):
        return _get_active_sub_category_count(obj)

    def validate(self, attrs):
        """
        Prevent cross-org parenting and cyclic hierarchy.

        - Parent must belong to the same organization
        - Category cannot be its own parent
        - Parent cannot be a descendant of this category
        """
        parent = attrs.get("parent")
        organization = attrs.get("organization") or (
            self.instance.organization if self.instance else None
        )
        instance = self.instance

        if parent:
            # Cross-org prevention
            if organization and parent.organization != organization:
                raise serializers.ValidationError(
                    {"parent": "Parent category must belong to the same organization."}
                )

            if instance:
                # Self-parent prevention
                if parent == instance:
                    raise serializers.ValidationError(
                        {"parent": "A category cannot be its own parent."}
                    )
                # Cycle detection — walk up from parent, ensure we don't reach instance
                seen = {instance.id}
                current = parent
                while current:
                    if current.id in seen:
                        raise serializers.ValidationError(
                            {
                                "parent": "Cyclic hierarchy detected: parent cannot be a descendant of this category."
                            }
                        )
                    seen.add(current.id)
                    current = current.parent

        return attrs


class AssetCategoryListSerializer(BaseSerializer):
    """Lightweight serializer for list views."""

    parent_name = serializers.CharField(
        source="parent.name",
        read_only=True,
        allow_null=True,
    )
    sub_category_count = serializers.SerializerMethodField()

    class Meta:
        model = AssetCategory
        fields = [
            "id",
            "cat_id",
            "name",
            "parent",
            "parent_name",
            "sub_category_count",
            "organization",
            "is_active",
        ]

    def get_sub_category_count(self, obj):
        return _get_active_sub_category_count(obj)


class AssetCategoryTreeSerializer(BaseSerializer):
    """
    Tree serializer for nested category hierarchy.
    Returns the category plus its direct sub-categories recursively.

    Accepts parent_map via context for N+1-free tree rendering.
    """

    sub_categories = serializers.SerializerMethodField()

    class Meta:
        model = AssetCategory
        fields = [
            "id",
            "cat_id",
            "name",
            "description",
            "parent",
            "sub_categories",
            "is_active",
        ]

    def get_sub_categories(self, obj):
        """Use parent_map from context if available, else query (fallback)."""
        parent_map = self.context.get("parent_map")
        if parent_map is not None:
            children = parent_map.get(obj.id, [])
        else:
            children = obj.sub_categories.active()
        return AssetCategoryTreeSerializer(
            children, many=True, context=self.context
        ).data
