"""
apps/assets/allocations/tests/test_models.py — Unit tests for Allocation model.
"""

import pytest

from apps.assets.allocations.models import Allocation
from apps.assets.inventory.models import Asset
from apps.assets.categories.models import AssetCategory


@pytest.mark.django_db
class TestAllocationModel:
    def test_allocation_created(self, organization, employee, asset):
        alloc = Allocation.objects.create(
            organization=organization,
            asset=asset,
            employee=employee,
            notes="Test allocation",
        )
        assert alloc.pk is not None
        assert alloc.alloc_id is not None
        assert alloc.alloc_id.startswith("ALC")
        assert alloc.asset == asset
        assert alloc.employee == employee
        assert alloc.is_current is True
        assert alloc.returned_at is None
        assert alloc.notes == "Test allocation"

    def test_allocation_is_current_true_when_not_returned(self, organization, employee, asset):
        alloc = Allocation.objects.create(
            organization=organization,
            asset=asset,
            employee=employee,
        )
        assert alloc.is_current is True

    def test_allocation_is_current_false_when_returned(self, organization, employee, asset):
        from django.utils import timezone

        alloc = Allocation.objects.create(
            organization=organization,
            asset=asset,
            employee=employee,
        )
        alloc.returned_at = timezone.now()
        alloc.save()
        assert alloc.is_current is False

    def test_allocation_soft_delete(self, organization, employee, asset):
        alloc = Allocation.objects.create(
            organization=organization,
            asset=asset,
            employee=employee,
        )
        alloc.delete()
        alloc.refresh_from_db()
        assert alloc.is_deleted is True
        assert alloc.deleted_at is not None

    def test_allocation_restore(self, organization, employee, asset):
        alloc = Allocation.objects.create(
            organization=organization,
            asset=asset,
            employee=employee,
        )
        alloc.delete()
        alloc.restore()
        assert alloc.is_deleted is False
        assert alloc.is_active is True  # BaseModel field
        assert alloc.is_current is True  # custom property
        assert alloc.deleted_at is None

    def test_allocation_unique_hrid(self, organization, employee, asset):
        """Each allocation gets a unique HRID."""
        import re
        from apps.assets.inventory.models import Asset

        a1 = Allocation.objects.create(organization=organization, asset=asset, employee=employee)
        # Use separate assets to avoid DB unique_active_allocation constraint
        a2_asset = Asset.objects.create(organization=organization, name="Asset 2")
        a3_asset = Asset.objects.create(organization=organization, name="Asset 3")
        a2 = Allocation.objects.create(organization=organization, asset=a2_asset, employee=employee)
        a3 = Allocation.objects.create(organization=organization, asset=a3_asset, employee=employee)
        # ALC + 6 alphanumeric chars
        assert re.match(r"ALC[A-Z0-9]{6}$", a1.alloc_id)
        assert a1.alloc_id != a2.alloc_id
        assert a2.alloc_id != a3.alloc_id

    def test_allocation_deleted_excluded_by_manager(self, organization, employee, asset):
        alloc = Allocation.objects.create(
            organization=organization,
            asset=asset,
            employee=employee,
        )
        alloc.delete()
        assert Allocation.objects.filter(alloc_id=alloc.alloc_id).count() == 0
        assert Allocation.all_objects.filter(alloc_id=alloc.alloc_id).count() == 1

    def test_allocation_str(self, organization, employee, asset):
        alloc = Allocation.objects.create(
            organization=organization,
            asset=asset,
            employee=employee,
        )
        assert asset.name in str(alloc)
        assert alloc.alloc_id in str(alloc)
