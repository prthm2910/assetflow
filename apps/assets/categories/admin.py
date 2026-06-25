"""
apps/assets/categories/admin.py — Admin configuration for Asset Categories.
"""

from django.contrib import admin

from apps.assets.categories.models import AssetCategory


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ["cat_id", "name", "parent", "organization", "is_active"]
    list_filter = ["is_active", "organization"]
    search_fields = ["name", "cat_id"]
    readonly_fields = ["cat_id"]
