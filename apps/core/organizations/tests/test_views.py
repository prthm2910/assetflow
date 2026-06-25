"""
apps/core/organizations/tests/test_views.py — Tests for Organization and OrganizationProfile viewsets.
"""

import pytest

from django.contrib.auth import get_user_model
from rest_framework import status

from apps.base.constants import UserRole
from apps.core.organizations.models import Organization


User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org(transactional_db):
    """Create a test organization."""
    return Organization.objects.create(
        name="Test Organization",
        slug="test-org",
        contact_email="admin@testorg.com",
        contact_phone="+1234567890",
        address="123 Test St",
        city="Testville",
        country="Testland",
    )


@pytest.fixture
def org_admin_user_with_org(db, org):
    """Org admin user assigned to an organization."""
    return User.objects.create_user(
        username="org_admin_user",
        email="org_admin_user@test.com",
        password="testpass123",
        first_name="Org",
        last_name="Admin",
        role=UserRole.ORG_ADMIN.value,
        organization_id=org.id,
    )


@pytest.fixture
def employee_user_with_org(db, org):
    """Employee user assigned to an organization."""
    return User.objects.create_user(
        username="employee_user",
        email="employee_user@test.com",
        password="testpass123",
        first_name="Test",
        last_name="Employee",
        role=UserRole.EMPLOYEE.value,
        organization_id=org.id,
    )


@pytest.fixture
def super_admin_client(api_client, super_admin_user):
    api_client.force_authenticate(user=super_admin_user)
    return api_client


@pytest.fixture
def org_admin_client(api_client, org_admin_user_with_org):
    api_client.force_authenticate(user=org_admin_user_with_org)
    return api_client


@pytest.fixture
def employee_client(api_client, employee_user_with_org):
    api_client.force_authenticate(user=employee_user_with_org)
    return api_client


# ---------------------------------------------------------------------------
# OrganizationViewSet Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOrganizationViewSetList:
    """Tests for GET /api/v1/organizations/."""

    def test_super_admin_sees_all_orgs(self, super_admin_client, org):
        """Super admin should see all organizations."""
        response = super_admin_client.get("/api/v1/organizations/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data

    def test_org_admin_sees_only_own_org(self, org_admin_client, org, db):
        """Org admin should see only their own organization."""
        # Create another org
        other_org = Organization.objects.create(
            name="Other Org",
            slug="other-org",
            contact_email="other@test.com",
        )
        response = org_admin_client.get("/api/v1/organizations/")
        assert response.status_code == status.HTTP_200_OK
        org_ids = [o["org_id"] for o in response.data.get("data", [])] + (
            [o["org_id"] for o in response.data.get("results", [])]
        )
        assert org.org_id in org_ids
        assert other_org.org_id not in org_ids

    def test_employee_sees_only_own_org(self, employee_client, org):
        """Employee should see only their own organization."""
        response = employee_client.get("/api/v1/organizations/")
        assert response.status_code == status.HTTP_200_OK
        org_ids = [o["org_id"] for o in response.data.get("data", [])] + (
            [o["org_id"] for o in response.data.get("results", [])]
        )
        assert org.org_id in org_ids

    def test_unauthenticated_denied(self, api_client):
        """Unauthenticated request should be denied."""
        response = api_client.get("/api/v1/organizations/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestOrganizationViewSetCreate:
    """Tests for POST /api/v1/organizations/."""

    def test_super_admin_can_create_org(self, super_admin_client):
        """Super admin should be able to create organizations."""
        response = super_admin_client.post(
            "/api/v1/organizations/",
            {
                "name": "New Org",
                "slug": "new-org",
                "contact_email": "new@org.com",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["data"]["name"] == "New Org"

    def test_org_admin_cannot_create_org(self, org_admin_client):
        """Org admin should not be able to create organizations."""
        response = org_admin_client.post(
            "/api/v1/organizations/",
            {
                "name": "Unauthorized Org",
                "slug": "unauth-org",
                "contact_email": "unauth@org.com",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_employee_cannot_create_org(self, employee_client):
        """Employee should not be able to create organizations."""
        response = employee_client.post(
            "/api/v1/organizations/",
            {
                "name": "Unauthorized Org",
                "slug": "unauth-org-2",
                "contact_email": "unauth2@org.com",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_org_with_duplicate_slug_fails(self, super_admin_client, org):
        """Creating org with duplicate slug should fail."""
        response = super_admin_client.post(
            "/api/v1/organizations/",
            {
                "name": "Duplicate Slug Org",
                "slug": org.slug,
                "contact_email": "dup@org.com",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestOrganizationViewSetRetrieve:
    """Tests for GET /api/v1/organizations/{org_id}/."""

    def test_super_admin_can_retrieve_any_org(self, super_admin_client, org):
        """Super admin can retrieve any organization."""
        response = super_admin_client.get(
            f"/api/v1/organizations/{org.org_id}/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["org_id"] == org.org_id

    def test_org_admin_can_retrieve_own_org(self, org_admin_client, org):
        """Org admin can retrieve their own organization."""
        response = org_admin_client.get(
            f"/api/v1/organizations/{org.org_id}/"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_employee_can_retrieve_own_org(self, employee_client, org):
        """Employee can retrieve their own organization."""
        response = employee_client.get(
            f"/api/v1/organizations/{org.org_id}/"
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestOrganizationViewSetUpdate:
    """Tests for PUT/PATCH /api/v1/organizations/{org_id}/."""

    def test_super_admin_can_update_org(self, super_admin_client, org):
        """Super admin can update organization."""
        response = super_admin_client.patch(
            f"/api/v1/organizations/{org.org_id}/",
            {"name": "Updated Org Name"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["name"] == "Updated Org Name"

    def test_org_admin_cannot_update_org(self, org_admin_client, org):
        """Org admin should not be able to update organization."""
        response = org_admin_client.patch(
            f"/api/v1/organizations/{org.org_id}/",
            {"name": "Hacked Name"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_employee_cannot_update_org(self, employee_client, org):
        """Employee should not be able to update organization."""
        response = employee_client.patch(
            f"/api/v1/organizations/{org.org_id}/",
            {"name": "Hacked Name"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestOrganizationViewSetDelete:
    """Tests for DELETE /api/v1/organizations/{org_id}/."""

    def test_super_admin_can_delete_org(self, super_admin_client, org):
        """Super admin can soft-delete organization."""
        response = super_admin_client.delete(
            f"/api/v1/organizations/{org.org_id}/"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_org_admin_cannot_delete_org(self, org_admin_client, org):
        """Org admin should not be able to delete organization."""
        response = org_admin_client.delete(
            f"/api/v1/organizations/{org.org_id}/"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_employee_cannot_delete_org(self, employee_client, org):
        """Employee should not be able to delete organization."""
        response = employee_client.delete(
            f"/api/v1/organizations/{org.org_id}/"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestToggleActive:
    """Tests for POST /api/v1/organizations/{org_id}/toggle-active/."""

    def test_super_admin_can_toggle_active(self, super_admin_client, org):
        """Super admin can toggle organization active status."""
        assert org.is_active is True
        response = super_admin_client.post(
            f"/api/v1/organizations/{org.org_id}/toggle-active/"
        )
        assert response.status_code == status.HTTP_200_OK
        org.refresh_from_db()
        assert org.is_active is False

        # Toggle back
        response = super_admin_client.post(
            f"/api/v1/organizations/{org.org_id}/toggle-active/"
        )
        org.refresh_from_db()
        assert org.is_active is True

    def test_non_super_admin_cannot_toggle(self, org_admin_client, org):
        """Non-super-admin should not be able to toggle."""
        response = org_admin_client.post(
            f"/api/v1/organizations/{org.org_id}/toggle-active/"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestOrganizationConfig:
    """Tests for GET/PATCH /api/v1/organizations/{org_id}/config/."""

    def test_get_config(self, super_admin_client, org):
        """GET config should return organization config."""
        response = super_admin_client.get(
            f"/api/v1/organizations/{org.org_id}/config/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "default_timezone" in response.data["data"]

    def test_super_admin_can_update_config(self, super_admin_client, org):
        """Super admin can update organization config."""
        response = super_admin_client.patch(
            f"/api/v1/organizations/{org.org_id}/config/",
            {
                "default_timezone": "America/New_York",
                "working_hours_start": "08:00:00",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["default_timezone"] == "America/New_York"

    def test_non_super_admin_cannot_update_config(self, org_admin_client, org):
        """Non-super-admin should not be able to update config."""
        response = org_admin_client.patch(
            f"/api/v1/organizations/{org.org_id}/config/",
            {"default_timezone": "Asia/Tokyo"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# OrganizationProfileViewSet Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestOrganizationProfileViewSet:
    """Tests for OrganizationProfileViewSet (GET/PATCH /api/v1/profile/)."""

    def test_get_own_org_profile(self, org, transactional_db):
        """Employee can get their own organization profile."""
        employee = User.objects.create_user(
            username="emp_profile",
            email="emp_profile@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Employee",
            role=UserRole.EMPLOYEE.value,
            organization_id=org.id,
        )
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=employee)
        response = client.get("/api/v1/organizations/profile/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["org_id"] == org.org_id
        assert "config" in response.data["data"]

    def test_org_admin_can_update_own_profile(self, org, transactional_db):
        """Org admin can update their own organization profile."""
        admin = User.objects.create_user(
            username="admin_profile",
            email="admin_profile@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Admin",
            role=UserRole.ORG_ADMIN.value,
            organization_id=org.id,
        )
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.patch(
            "/api/v1/organizations/profile/",
            {"contact_phone": "+9876543210"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["contact_phone"] == "+9876543210"

    def test_employee_cannot_update_profile(self, employee_client, org):
        """Employee cannot update organization profile."""
        response = employee_client.patch(
            "/api/v1/organizations/profile/",
            {"contact_phone": "+9999999999"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_without_org_gets_404(self, transactional_db):
        """User without an organization should get 404 on profile."""
        orphan = User.objects.create_user(
            username="orphan_user",
            email="orphan@test.com",
            password="testpass123",
            first_name="No",
            last_name="Org",
            role=UserRole.EMPLOYEE.value,
            organization_id=None,
        )
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=orphan)
        response = client.get("/api/v1/organizations/profile/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
