"""
apps/assets/categories/tests/test_models.py — Unit tests for AssetCategory model.
"""

import pytest

from apps.assets.categories.models import AssetCategory


@pytest.mark.django_db
class TestAssetCategoryModel:
    def test_category_created_with_org(self, organization):
        cat = AssetCategory.objects.create(
            organization=organization,
            name="Laptops",
            description="Portable computing devices",
        )
        assert cat.pk is not None
        assert cat.cat_id is not None
        assert cat.cat_id.startswith("CAT")
        assert cat.organization == organization
        assert cat.name == "Laptops"
        assert cat.is_active is True
        assert cat.is_deleted is False
        assert cat.parent is None

    def test_category_with_parent(self, organization):
        parent = AssetCategory.objects.create(
            organization=organization,
            name="Electronics",
        )
        child = AssetCategory.objects.create(
            organization=organization,
            name="Laptops",
            parent=parent,
        )
        assert child.parent == parent
        assert child in parent.sub_categories.all()

    def test_category_unique_together_per_org(self, organization, second_organization):
        AssetCategory.objects.create(organization=organization, name="Laptops")
        # Same name in different org — allowed
        cat2 = AssetCategory.objects.create(
            organization=second_organization, name="Laptops"
        )
        assert cat2.pk is not None

    def test_category_unique_together_same_org_fails(self, organization):
        AssetCategory.objects.create(organization=organization, name="Laptops")
        with pytest.raises(Exception):  # IntegrityError
            AssetCategory.objects.create(organization=organization, name="Laptops")

    def test_category_soft_delete(self, organization):
        cat = AssetCategory.objects.create(organization=organization, name="Laptops")
        cat.delete()
        cat.refresh_from_db()
        assert cat.is_deleted is True
        assert cat.deleted_at is not None

    def test_category_restore(self, organization):
        cat = AssetCategory.objects.create(organization=organization, name="Laptops")
        cat.delete()
        cat.restore()
        assert cat.is_deleted is False
        assert cat.is_active is True
        assert cat.deleted_at is None

    def test_category_str(self, organization):
        cat = AssetCategory.objects.create(organization=organization, name="Laptops")
        assert cat.name in str(cat)
        assert cat.cat_id in str(cat)

    def test_category_nested_hierarchy(self, organization):
        """A 3-level category tree: Computers > Laptops > Gaming Laptops."""
        computers = AssetCategory.objects.create(
            organization=organization,
            name="Computers",
        )
        laptops = AssetCategory.objects.create(
            organization=organization,
            name="Laptops",
            parent=computers,
        )
        gaming = AssetCategory.objects.create(
            organization=organization,
            name="Gaming Laptops",
            parent=laptops,
        )
        assert gaming.parent == laptops
        assert laptops.parent == computers
        assert gaming in laptops.sub_categories.all()
        assert laptops in computers.sub_categories.all()

    def test_category_deleted_excluded_by_manager(self, organization):
        """Soft-deleted categories are excluded from default manager."""
        cat = AssetCategory.objects.create(organization=organization, name="Laptops")
        cat.delete()
        # Default manager should not see it
        assert AssetCategory.objects.filter(name="Laptops").count() == 0
        # all_objects should still see it
        assert AssetCategory.all_objects.filter(name="Laptops").count() == 1
