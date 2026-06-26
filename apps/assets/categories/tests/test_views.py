"""
apps/assets/categories/tests/test_views.py — API tests for AssetCategory endpoints.
"""

import pytest

from apps.assets.categories.models import AssetCategory


@pytest.mark.django_db
class TestAssetCategoryListCreate:
    """Test list and create endpoints."""

    def test_super_admin_can_list_all_orgs(
        self, super_admin_client, organization, second_organization
    ):
        AssetCategory.objects.create(organization=organization, name="Laptops")
        AssetCategory.objects.create(organization=second_organization, name="Desktops")
        response = super_admin_client.get("/api/v1/assets/categories/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["count"] == 2

    def test_org_admin_can_list_own_org(
        self, org_admin_client, organization, second_organization
    ):
        AssetCategory.objects.create(organization=organization, name="Laptops")
        AssetCategory.objects.create(organization=second_organization, name="Desktops")
        response = org_admin_client.get("/api/v1/assets/categories/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["count"] == 1
        assert data["results"][0]["name"] == "Laptops"

    def test_employee_can_list_own_org(
        self, employee_client, organization, second_organization
    ):
        AssetCategory.objects.create(organization=organization, name="Laptops")
        AssetCategory.objects.create(organization=second_organization, name="Desktops")
        response = employee_client.get("/api/v1/assets/categories/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_unauthenticated_denied(self, api_client):
        response = api_client.get("/api/v1/assets/categories/")
        assert response.status_code == 401

    def test_org_admin_can_create(self, org_admin_client, organization):
        response = org_admin_client.post(
            "/api/v1/assets/categories/",
            {"name": "Laptops", "description": "Portable computers", "organization": str(organization.id)},
        )
        assert response.status_code == 201
        assert response.json()["data"]["name"] == "Laptops"
        assert response.json()["data"]["cat_id"].startswith("CAT")

    def test_super_admin_can_create(self, super_admin_client, organization):
        response = super_admin_client.post(
            "/api/v1/assets/categories/",
            {"name": "Monitors", "organization": str(organization.id)},
        )
        assert response.status_code == 201

    def test_employee_cannot_create(self, employee_client, organization):
        response = employee_client.post(
            "/api/v1/assets/categories/",
            {"name": "Laptops", "organization": str(organization.id)},
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestAssetCategoryRetrieveUpdateDestroy:
    """Test retrieve, update, and destroy endpoints."""

    def test_retrieve_category(self, org_admin_client, organization):
        cat = AssetCategory.objects.create(organization=organization, name="Laptops")
        response = org_admin_client.get(f"/api/v1/assets/categories/{cat.cat_id}/")
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Laptops"
        assert response.json()["data"]["cat_id"] == cat.cat_id

    def test_update_category(self, org_admin_client, organization):
        cat = AssetCategory.objects.create(organization=organization, name="Laptops")
        response = org_admin_client.patch(
            f"/api/v1/assets/categories/{cat.cat_id}/",
            {"name": "Gaming Laptops"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Gaming Laptops"

    def test_delete_category(self, org_admin_client, organization):
        cat = AssetCategory.objects.create(organization=organization, name="Laptops")
        response = org_admin_client.delete(f"/api/v1/assets/categories/{cat.cat_id}/")
        assert response.status_code == 204
        cat.refresh_from_db()
        assert cat.is_deleted is True

    def test_employee_cannot_delete(self, employee_client, organization):
        cat = AssetCategory.objects.create(organization=organization, name="Laptops")
        response = employee_client.delete(f"/api/v1/assets/categories/{cat.cat_id}/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestAssetCategoryTree:
    """Test tree and descendants custom actions."""

    def test_tree_returns_top_level_only(self, org_admin_client, organization):
        """Tree action returns only root categories (parent=null)."""
        parent = AssetCategory.objects.create(organization=organization, name="Computers")
        AssetCategory.objects.create(organization=organization, name="Laptops", parent=parent)
        response = org_admin_client.get("/api/v1/assets/categories/tree/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["count"] == 1
        assert data["results"][0]["name"] == "Computers"

    def test_tree_includes_nested_children(self, org_admin_client, organization):
        """Tree serializer should include sub-categories recursively."""
        parent = AssetCategory.objects.create(organization=organization, name="Computers")
        child = AssetCategory.objects.create(
            organization=organization, name="Laptops", parent=parent
        )
        AssetCategory.objects.create(
            organization=organization, name="Gaming Laptops", parent=child
        )
        response = org_admin_client.get("/api/v1/assets/categories/tree/")
        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert len(results) == 1
        assert results[0]["name"] == "Computers"
        assert len(results[0]["sub_categories"]) == 1
        assert results[0]["sub_categories"][0]["name"] == "Laptops"

    def test_descendants_returns_flat_list(self, org_admin_client, organization):
        """Descendants action returns all children, grandchildren, etc. as flat list."""
        parent = AssetCategory.objects.create(organization=organization, name="Computers")
        child = AssetCategory.objects.create(
            organization=organization, name="Laptops", parent=parent
        )
        AssetCategory.objects.create(
            organization=organization, name="Gaming Laptops", parent=child
        )
        response = org_admin_client.get(
            f"/api/v1/assets/categories/{parent.cat_id}/descendants/"
        )
        assert response.status_code == 200
        names = [c["name"] for c in response.json()["data"]]
        assert "Laptops" in names
        assert "Gaming Laptops" in names


@pytest.mark.django_db
class TestAssetCategoryMultiTenant:
    """Test row-level isolation across organizations."""

    def test_org_admin_sees_only_own_categories(
        self, org_admin_client, organization, second_organization
    ):
        """Org admin cannot see or modify categories from other orgs."""
        AssetCategory.objects.create(organization=organization, name="Laptops")
        AssetCategory.objects.create(organization=second_organization, name="Desktops")
        response = org_admin_client.get("/api/v1/assets/categories/")
        assert response.json()["data"]["count"] == 1

    def test_cross_org_retrieve_returns_404(self, org_admin_client, second_organization):
        """Org admin cannot retrieve another org's category."""
        other_cat = AssetCategory.objects.create(
            organization=second_organization, name="Desktops"
        )
        response = org_admin_client.get(
            f"/api/v1/assets/categories/{other_cat.cat_id}/"
        )
        assert response.status_code == 404
