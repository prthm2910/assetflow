"""
apps/assets/inventory/tests/test_models.py — Unit tests for Asset model.
"""

import pytest

from apps.assets.inventory.models import Asset


@pytest.mark.django_db
class TestAssetModel:
    def test_asset_created_with_org(self, organization):
        asset = Asset.objects.create(
            organization=organization,
            name="MacBook Pro 16",
            description="Apple laptop for development",
        )
        assert asset.pk is not None
        assert asset.asset_id is not None
        assert asset.asset_id.startswith("AST")
        assert asset.organization == organization
        assert asset.name == "MacBook Pro 16"
        assert asset.is_active is True
        assert asset.is_deleted is False

    def test_asset_with_category(self, organization):
        from apps.assets.categories.models import AssetCategory

        cat = AssetCategory.objects.create(organization=organization, name="Laptops")
        asset = Asset.objects.create(
            organization=organization,
            name="MacBook Pro",
            category=cat,
        )
        assert asset.category == cat

    def test_asset_with_assigned_employee(self, organization, employee):
        asset = Asset.objects.create(
            organization=organization,
            name="Dell Laptop",
            assigned_to=employee,
        )
        assert asset.assigned_to == employee

    def test_asset_unique_codes(self, organization):
        """Each new asset gets a unique HRID (AST + 6 random chars)."""
        import re
        a1 = Asset.objects.create(organization=organization, name="Asset 1")
        a2 = Asset.objects.create(organization=organization, name="Asset 2")
        a3 = Asset.objects.create(organization=organization, name="Asset 3")
        # Codes should be unique: AST + 6 alphanumeric chars
        assert re.match(r"AST[A-Z0-9]{6}$", a1.asset_id)
        assert a1.asset_id != a2.asset_id
        assert a2.asset_id != a3.asset_id

    def test_asset_soft_delete(self, organization):
        asset = Asset.objects.create(organization=organization, name="Monitor")
        asset.delete()
        asset.refresh_from_db()
        assert asset.is_deleted is True
        assert asset.deleted_at is not None

    def test_asset_restore(self, organization):
        asset = Asset.objects.create(organization=organization, name="Keyboard")
        asset.delete()
        asset.restore()
        assert asset.is_deleted is False
        assert asset.is_active is True
        assert asset.deleted_at is None

    def test_asset_str(self, organization):
        asset = Asset.objects.create(organization=organization, name="Mouse")
        assert asset.name in str(asset)
        assert asset.asset_id in str(asset)

    def test_asset_deleted_excluded_by_manager(self, organization):
        """Soft-deleted assets are excluded from default manager."""
        asset = Asset.objects.create(organization=organization, name="Headset")
        asset.delete()
        assert Asset.objects.filter(name="Headset").count() == 0
        assert Asset.all_objects.filter(name="Headset").count() == 1

    def test_asset_default_status(self, organization):
        """New assets default to 'available' status."""
        from apps.assets.inventory.constants import AssetStatus
        asset = Asset.objects.create(organization=organization, name="Webcam")
        assert asset.status == AssetStatus.AVAILABLE.value
