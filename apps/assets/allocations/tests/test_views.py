"""
apps/assets/allocations/tests/test_views.py — API tests for Allocation endpoints.
"""

import pytest

from apps.assets.allocations.models import Allocation
from apps.assets.inventory.models import Asset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_allocation(client, organization, asset, employee, notes=""):
    """Create an allocation via API and return the response."""
    return client.post(
        "/api/v1/assets/allocations/",
        {
            "asset": str(asset.id),
            "employee": str(employee.id),
            "notes": notes,
        },
    )


# ---------------------------------------------------------------------------
# List / Create
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAllocationListCreate:
    def test_super_admin_can_list_all_orgs(
        self, super_admin_client, organization, second_organization,
        employee, second_employee, asset
    ):
        """Super admin sees allocations across all organizations."""
        # Org 1 allocation
        Allocation.objects.create(organization=organization, asset=asset, employee=employee)
        # Org 2 setup
        from apps.assets.inventory.models import Asset
        other_asset = Asset.objects.create(
            organization=second_organization,
            name="Other Laptop",
        )
        Allocation.objects.create(
            organization=second_organization,
            asset=other_asset,
            employee=second_employee,
        )
        response = super_admin_client.get("/api/v1/assets/allocations/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 2

    def test_org_admin_sees_own_org_only(
        self, org_admin_client, organization, second_organization,
        employee, second_employee, asset
    ):
        """Org admin sees only allocations in their own org."""
        Allocation.objects.create(organization=organization, asset=asset, employee=employee)
        from apps.assets.inventory.models import Asset
        other_asset = Asset.objects.create(
            organization=second_organization,
            name="Other Laptop",
        )
        Allocation.objects.create(
            organization=second_organization,
            asset=other_asset,
            employee=second_employee,
        )
        response = org_admin_client.get("/api/v1/assets/allocations/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_employee_sees_only_own_allocations(
        self, employee_client, organization, employee, asset, second_employee
    ):
        """Employee sees only allocations assigned to their own employee record."""
        # Use separate assets to avoid unique_active_allocation constraint
        other_asset = Asset.objects.create(
            organization=organization, name="Second Laptop"
        )
        Allocation.objects.create(organization=organization, asset=asset, employee=employee)
        Allocation.objects.create(
            organization=organization, asset=other_asset, employee=second_employee
        )
        response = employee_client.get("/api/v1/assets/allocations/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_unauthenticated_denied(self, api_client):
        response = api_client.get("/api/v1/assets/allocations/")
        assert response.status_code == 401

    def test_org_admin_can_create(
        self, org_admin_client, organization, employee, asset
    ):
        """Org admin can allocate an asset to an employee."""
        response = create_allocation(org_admin_client, organization, asset, employee)
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["asset"] == str(asset.id)
        assert data["employee"] == str(employee.id)
        assert data["is_current"] is True
        assert data["alloc_id"].startswith("ALC")

    def test_super_admin_can_create(self, super_admin_client, organization, employee, asset):
        """Super admin can allocate assets across any org."""
        response = create_allocation(super_admin_client, organization, asset, employee)
        assert response.status_code == 201

    def test_employee_cannot_create(
        self, employee_client, organization, employee, asset
    ):
        """Employees cannot create allocations."""
        response = create_allocation(employee_client, organization, asset, employee)
        assert response.status_code == 403

    def test_cannot_allocate_already_allocated_asset(
        self, org_admin_client, organization, employee
    ):
        """Cannot allocate an already-allocated asset."""
        # Create a fresh asset for this test to avoid fixture pollution
        from apps.assets.inventory.models import Asset
        fresh_asset = Asset.objects.create(
            organization=organization,
            name="Already Allocated Laptop",
        )
        Allocation.objects.create(
            organization=organization, asset=fresh_asset, employee=employee
        )
        response = create_allocation(org_admin_client, organization, fresh_asset, employee)
        assert response.status_code == 400

    def test_cannot_allocate_retired_asset(
        self, org_admin_client, organization, employee, asset
    ):
        """Cannot allocate a retired asset."""
        asset.status = "retired"
        asset.save(update_fields=["status"])
        response = create_allocation(org_admin_client, organization, asset, employee)
        assert response.status_code == 400

    def test_create_updates_asset_status_to_allocated(
        self, org_admin_client, organization, employee, asset
    ):
        """Allocating an asset sets its status to 'allocated'."""
        assert asset.status == "available"
        response = create_allocation(org_admin_client, organization, asset, employee)
        assert response.status_code == 201
        asset.refresh_from_db()
        assert asset.status == "allocated"


# ---------------------------------------------------------------------------
# Retrieve / Update / Delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAllocationRetrieveUpdateDelete:
    def test_can_retrieve_allocation(
        self, org_admin_client, organization, employee, asset
    ):
        alloc = Allocation.objects.create(
            organization=organization, asset=asset, employee=employee
        )
        response = org_admin_client.get(
            f"/api/v1/assets/allocations/{alloc.alloc_id}/"
        )
        assert response.status_code == 200
        assert response.json()["data"]["alloc_id"] == alloc.alloc_id

    def test_can_partial_update_allocation(
        self, org_admin_client, organization, employee, asset
    ):
        alloc = Allocation.objects.create(
            organization=organization, asset=asset, employee=employee
        )
        response = org_admin_client.patch(
            f"/api/v1/assets/allocations/{alloc.alloc_id}/",
            {"notes": "Updated notes"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["notes"] == "Updated notes"

    def test_can_delete_allocation(
        self, org_admin_client, organization, employee, asset
    ):
        alloc = Allocation.objects.create(
            organization=organization, asset=asset, employee=employee
        )
        response = org_admin_client.delete(
            f"/api/v1/assets/allocations/{alloc.alloc_id}/"
        )
        assert response.status_code == 204
        alloc.refresh_from_db()
        assert alloc.is_deleted is True

    def test_delete_active_allocation_reverts_asset_status(
        self, org_admin_client, organization, employee, asset
    ):
        """Deleting an active allocation reverts asset status to 'available'."""
        alloc = Allocation.objects.create(
            organization=organization, asset=asset, employee=employee
        )
        asset.status = "allocated"
        asset.save(update_fields=["status"])

        response = org_admin_client.delete(
            f"/api/v1/assets/allocations/{alloc.alloc_id}/"
        )
        assert response.status_code == 204
        asset.refresh_from_db()
        assert asset.status == "available"

    def test_employee_cannot_update(
        self, employee_client, organization, employee, asset
    ):
        alloc = Allocation.objects.create(
            organization=organization, asset=asset, employee=employee
        )
        response = employee_client.patch(
            f"/api/v1/assets/allocations/{alloc.alloc_id}/",
            {"notes": "Hacked"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Transfer
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAllocationTransfer:
    def test_transfer_creates_new_active_allocation(
        self, org_admin_client, organization, employee, second_employee, asset
    ):
        """Transfer creates a new allocation for the new employee."""
        alloc = Allocation.objects.create(
            organization=organization, asset=asset, employee=employee
        )
        response = org_admin_client.post(
            f"/api/v1/assets/allocations/{alloc.alloc_id}/transfer/",
            {"employee": str(second_employee.id), "notes": "Transfer to QA"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["employee"] == str(second_employee.id)
        assert data["is_current"] is True

    def test_transfer_closes_original_allocation(
        self, org_admin_client, organization, employee, second_employee, asset
    ):
        """Transfer closes the original allocation (sets returned_at)."""
        alloc = Allocation.objects.create(
            organization=organization, asset=asset, employee=employee
        )
        response = org_admin_client.post(
            f"/api/v1/assets/allocations/{alloc.alloc_id}/transfer/",
            {"employee": str(second_employee.id)},
        )
        assert response.status_code == 201
        alloc.refresh_from_db()
        assert alloc.is_current is False
        assert alloc.returned_at is not None

    def test_transfer_cannot_transfer_returned_allocation(
        self, org_admin_client, organization, employee, asset
    ):
        """Cannot transfer an already-returned allocation."""
        from django.utils import timezone
        alloc = Allocation.objects.create(
            organization=organization, asset=asset, employee=employee
        )
        alloc.returned_at = timezone.now()
        alloc.save(update_fields=["returned_at"])
        response = org_admin_client.post(
            f"/api/v1/assets/allocations/{alloc.alloc_id}/transfer/",
            {"employee": str(employee.id)},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Return Asset
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAllocationReturnAsset:
    def test_return_asset_closes_allocation(
        self, org_admin_client, organization, employee, asset
    ):
        """Returning an asset sets returned_at on the allocation."""
        alloc = Allocation.objects.create(
            organization=organization, asset=asset, employee=employee
        )
        response = org_admin_client.post(
            f"/api/v1/assets/allocations/{alloc.alloc_id}/return/",
            {"notes": "Returned for repair"},
        )
        assert response.status_code == 200
        alloc.refresh_from_db()
        assert alloc.is_current is False
        assert alloc.returned_at is not None

    def test_return_asset_reverts_asset_status(
        self, org_admin_client, organization, employee, asset
    ):
        """Returning an asset reverts its status to 'available'."""
        asset.status = "allocated"
        asset.save(update_fields=["status"])
        alloc = Allocation.objects.create(
            organization=organization, asset=asset, employee=employee
        )
        response = org_admin_client.post(
            f"/api/v1/assets/allocations/{alloc.alloc_id}/return/"
        )
        assert response.status_code == 200
        asset.refresh_from_db()
        assert asset.status == "available"

    def test_return_cannot_return_already_returned(
        self, org_admin_client, organization, employee, asset
    ):
        """Cannot return an already-returned allocation."""
        from django.utils import timezone
        alloc = Allocation.objects.create(
            organization=organization, asset=asset, employee=employee
        )
        alloc.returned_at = timezone.now()
        alloc.save(update_fields=["returned_at"])
        response = org_admin_client.post(
            f"/api/v1/assets/allocations/{alloc.alloc_id}/return/"
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Current (active only)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAllocationCurrent:
    def test_current_shows_only_active_allocations(
        self, org_admin_client, organization, employee, asset
    ):
        """GET /allocations/current/ returns only unreturned allocations."""
        from django.utils import timezone

        # Use separate assets to avoid unique_active_allocation constraint
        other_asset = Asset.objects.create(
            organization=organization, name="Returned Laptop"
        )
        active = Allocation.objects.create(
            organization=organization, asset=asset, employee=employee
        )
        returned = Allocation.objects.create(
            organization=organization, asset=other_asset, employee=employee
        )
        returned.returned_at = timezone.now()
        returned.save(update_fields=["returned_at"])

        response = org_admin_client.get("/api/v1/assets/allocations/current/")
        assert response.status_code == 200
        count = response.json()["data"]["count"]
        ids = [r["alloc_id"] for r in response.json()["data"]["results"]]
        assert count == 1
        assert active.alloc_id in ids
        assert returned.alloc_id not in ids


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAllocationFiltering:
    def test_filter_by_asset_id(
        self, org_admin_client, organization, employee, asset
    ):
        """Filter allocations by asset HRID."""
        from apps.assets.inventory.models import Asset

        other_asset = Asset.objects.create(
            organization=organization, name="Other Asset"
        )
        Allocation.objects.create(organization=organization, asset=asset, employee=employee)
        Allocation.objects.create(
            organization=organization, asset=other_asset, employee=employee
        )
        response = org_admin_client.get(
            f"/api/v1/assets/allocations/?asset_id={asset.asset_id}"
        )
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_filter_by_status_active(
        self, org_admin_client, organization, employee, asset
    ):
        """Filter by status=active returns only unreturned allocations."""
        from django.utils import timezone

        # Use separate assets to avoid unique_active_allocation constraint
        other_asset = Asset.objects.create(
            organization=organization, name="Returned Laptop"
        )
        Allocation.objects.create(organization=organization, asset=asset, employee=employee)
        returned = Allocation.objects.create(
            organization=organization, asset=other_asset, employee=employee
        )
        returned.returned_at = timezone.now()
        returned.save(update_fields=["returned_at"])

        response = org_admin_client.get("/api/v1/assets/allocations/?status=active")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_filter_by_status_returned(
        self, org_admin_client, organization, employee, asset
    ):
        """Filter by status=returned returns only returned allocations."""
        from django.utils import timezone

        # Use separate assets to avoid unique_active_allocation constraint
        other_asset = Asset.objects.create(
            organization=organization, name="Returned Laptop"
        )
        Allocation.objects.create(organization=organization, asset=asset, employee=employee)
        returned = Allocation.objects.create(
            organization=organization, asset=other_asset, employee=employee
        )
        returned.returned_at = timezone.now()
        returned.save(update_fields=["returned_at"])

        response = org_admin_client.get("/api/v1/assets/allocations/?status=returned")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1
