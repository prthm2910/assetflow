"""
apps/assets/inventory/tests/test_views.py — API tests for Asset endpoints.
"""

import pytest

from apps.assets.inventory.models import Asset


@pytest.mark.django_db
class TestAssetListCreate:
    """Test list and create endpoints."""

    def test_super_admin_can_list_all_orgs(
        self, super_admin_client, organization, second_organization
    ):
        Asset.objects.create(organization=organization, name="Laptop A")
        Asset.objects.create(organization=second_organization, name="Laptop B")
        response = super_admin_client.get("/api/v1/assets/inventory/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["count"] == 2

    def test_org_admin_can_list_own_org(
        self, org_admin_client, organization, second_organization
    ):
        Asset.objects.create(organization=organization, name="Laptop A")
        Asset.objects.create(organization=second_organization, name="Laptop B")
        response = org_admin_client.get("/api/v1/assets/inventory/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["count"] == 1
        assert data["results"][0]["name"] == "Laptop A"

    def test_employee_can_list_own_org(
        self, employee_client, organization, second_organization
    ):
        Asset.objects.create(organization=organization, name="Laptop A")
        Asset.objects.create(organization=second_organization, name="Laptop B")
        response = employee_client.get("/api/v1/assets/inventory/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_unauthenticated_denied(self, api_client):
        response = api_client.get("/api/v1/assets/inventory/")
        assert response.status_code == 401

    def test_org_admin_can_create(self, org_admin_client, organization):
        response = org_admin_client.post(
            "/api/v1/assets/inventory/",
            {
                "name": "MacBook Pro",
                "description": "Development laptop",
                "serial_number": "C02XG1YJHD6P",
                "brand": "Apple",
                "model_name": "MacBook Pro 16",
            },
        )
        assert response.status_code == 201
        assert response.json()["data"]["name"] == "MacBook Pro"
        assert response.json()["data"]["asset_id"].startswith("AST")
        assert response.json()["data"]["organization"] == str(organization.id)

    def test_super_admin_can_create(self, super_admin_client, organization):
        response = super_admin_client.post(
            "/api/v1/assets/inventory/",
            {"name": "Dell Monitor", "organization": str(organization.id)},
        )
        assert response.status_code == 201
        assert response.json()["data"]["name"] == "Dell Monitor"

    def test_employee_cannot_create(self, employee_client, organization):
        response = employee_client.post(
            "/api/v1/assets/inventory/",
            {"name": "Unauthorized Asset", "organization": str(organization.id)},
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestAssetRetrieveUpdateDelete:
    """Test retrieve, update, partial_update, and destroy."""

    def test_can_retrieve_asset(self, org_admin_client, organization):
        asset = Asset.objects.create(organization=organization, name="Laptop X")
        response = org_admin_client.get(f"/api/v1/assets/inventory/{asset.asset_id}/")
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Laptop X"

    def test_can_update_asset(self, org_admin_client, organization):
        asset = Asset.objects.create(organization=organization, name="Old Name")
        response = org_admin_client.put(
            f"/api/v1/assets/inventory/{asset.asset_id}/",
            {
                "name": "New Name",
                "description": "Updated description",
                "organization": str(organization.id),
                "status": asset.status,
            },
        )
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "New Name"

    def test_can_partial_update_asset(self, org_admin_client, organization):
        asset = Asset.objects.create(organization=organization, name="Laptop Y")
        response = org_admin_client.patch(
            f"/api/v1/assets/inventory/{asset.asset_id}/",
            {"name": "Laptop Z Updated"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Laptop Z Updated"

    def test_can_delete_asset(self, org_admin_client, organization):
        asset = Asset.objects.create(organization=organization, name="Laptop D")
        response = org_admin_client.delete(f"/api/v1/assets/inventory/{asset.asset_id}/")
        assert response.status_code == 204
        asset.refresh_from_db()
        assert asset.is_deleted is True

    def test_employee_cannot_update(self, employee_client, organization):
        asset = Asset.objects.create(organization=organization, name="Laptop E")
        response = employee_client.patch(
            f"/api/v1/assets/inventory/{asset.asset_id}/",
            {"name": "Hacked Name"},
        )
        assert response.status_code == 403

    def test_employee_cannot_delete(self, employee_client, organization):
        asset = Asset.objects.create(organization=organization, name="Laptop F")
        response = employee_client.delete(f"/api/v1/assets/inventory/{asset.asset_id}/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestAssetChangeStatus:
    """Test change_status custom action."""

    def test_change_status_valid(self, org_admin_client, organization):
        asset = Asset.objects.create(organization=organization, name="Laptop S")
        response = org_admin_client.patch(
            f"/api/v1/assets/inventory/{asset.asset_id}/change-status/",
            {"status": "maintenance"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "maintenance"

    def test_change_status_invalid(self, org_admin_client, organization):
        asset = Asset.objects.create(organization=organization, name="Laptop T")
        response = org_admin_client.patch(
            f"/api/v1/assets/inventory/{asset.asset_id}/change-status/",
            {"status": "invalid_status"},
        )
        assert response.status_code == 400

    def test_change_status_requires_auth(self, api_client, organization):
        asset = Asset.objects.create(organization=organization, name="Laptop U")
        response = api_client.patch(
            f"/api/v1/assets/inventory/{asset.asset_id}/change-status/",
            {"status": "maintenance"},
        )
        assert response.status_code == 401

    def test_employee_cannot_change_status(self, employee_client, organization):
        asset = Asset.objects.create(organization=organization, name="Laptop V")
        response = employee_client.patch(
            f"/api/v1/assets/inventory/{asset.asset_id}/change-status/",
            {"status": "retired"},
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestAssetFiltering:
    """Test filtering, search, and ordering."""

    def test_filter_by_status(self, org_admin_client, organization):
        Asset.objects.create(
            organization=organization, name="F-Avail-Laptop", status="available"
        )
        Asset.objects.create(
            organization=organization, name="F-Alloc-Desktop", status="allocated"
        )
        Asset.objects.create(
            organization=organization, name="F-Avail-Monitor", status="available"
        )
        response = org_admin_client.get("/api/v1/assets/inventory/?status=available")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 2

    def test_search_by_name(self, org_admin_client, organization):
        Asset.objects.create(
            organization=organization, name="F-Avail-Laptop", status="available"
        )
        Asset.objects.create(
            organization=organization, name="F-Alloc-Desktop", status="allocated"
        )
        Asset.objects.create(
            organization=organization, name="F-Avail-Monitor", status="available"
        )
        response = org_admin_client.get("/api/v1/assets/inventory/?search=F-Avail")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 2

    def test_ordering(self, org_admin_client, organization):
        Asset.objects.create(
            organization=organization, name="F-Alloc-Desktop", status="allocated"
        )
        Asset.objects.create(
            organization=organization, name="F-Avail-Laptop", status="available"
        )
        Asset.objects.create(
            organization=organization, name="F-Avail-Monitor", status="available"
        )
        response = org_admin_client.get("/api/v1/assets/inventory/?ordering=name")
        assert response.status_code == 200
        names = [r["name"] for r in response.json()["data"]["results"]]
        # Case-sensitive ordering: F-A < F-Av (ASCII: 'A'=65 < 'v'=118)
        assert names == ["F-Alloc-Desktop", "F-Avail-Laptop", "F-Avail-Monitor"]


@pytest.mark.django_db
class TestAssetMultiTenant:
    """Test cross-org isolation."""

    def test_cannot_view_other_org_asset(
        self, org_admin_client, second_organization, organization
    ):
        """Org admin sees only their own org's assets."""
        Asset.objects.create(organization=organization, name="My Org Asset")
        Asset.objects.create(organization=second_organization, name="Other Org Asset")
        response = org_admin_client.get("/api/v1/assets/inventory/")
        assert response.status_code == 200
        names = [r["name"] for r in response.json()["data"]["results"]]
        assert "My Org Asset" in names
        assert "Other Org Asset" not in names

    def test_cannot_update_other_org_asset(
        self, org_admin_client, second_organization, organization
    ):
        """Org admin cannot update assets from another org."""
        other_asset = Asset.objects.create(
            organization=second_organization, name="Other Asset"
        )
        response = org_admin_client.patch(
            f"/api/v1/assets/inventory/{other_asset.asset_id}/",
            {"name": "Hacked"},
        )
        assert response.status_code == 404
