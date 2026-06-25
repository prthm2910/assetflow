"""
apps/assets/categories/serializers.py — Serializers for AssetCategory.
"""

from rest_framework import serializers

from apps.base.serializers import BaseSerializer
from apps.assets.categories.models import AssetCategory


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
        return obj.sub_categories.filter(is_deleted=False, is_active=True).count()


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
        return obj.sub_categories.filter(is_deleted=False, is_active=True).count()


class AssetCategoryTreeSerializer(BaseSerializer):
    """
    Tree serializer for nested category hierarchy.
    Returns the category plus its direct sub-categories recursively.
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
        children = obj.sub_categories.filter(is_deleted=False, is_active=True)
        return AssetCategoryTreeSerializer(children, many=True).data
