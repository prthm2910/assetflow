"""apps/operations/licenses/tests/test_views.py — API tests for License endpoints."""

import pytest

from apps.base.constants import UserRole
from apps.operations.licenses.constants import LicenseType
from apps.operations.licenses.models import SoftwareLicense, LicenseAssignment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_license(client, organization, software_name="Test Software", license_type="per_user", total_seats=10, **kwargs):
    """Create a license via API and return the response."""
    return client.post(
        "/api/v1/licenses/",
        {
            "software_name": software_name,
            "license_type": license_type,
            "total_seats": total_seats,
            "organization": str(organization.id),
            **kwargs,
        },
    )


# ---------------------------------------------------------------------------
# List / Create
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLicenseListCreate:
    def test_super_admin_can_list_all_orgs(
        self, super_admin_client, organization, second_organization
    ):
        """Super admin sees licenses across all organizations."""
        SoftwareLicense.objects.create(
            organization=organization, software_name="Office",
            license_type=LicenseType.PER_USER.value, total_seats=10,
        )
        SoftwareLicense.objects.create(
            organization=second_organization, software_name="Adobe",
            license_type=LicenseType.PER_DEVICE.value, total_seats=5,
        )
        response = super_admin_client.get("/api/v1/licenses/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 2

    def test_org_admin_sees_own_org_only(
        self, org_admin_client, organization, second_organization
    ):
        """Org admin sees only licenses in their organization."""
        SoftwareLicense.objects.create(
            organization=organization, software_name="Office",
            license_type=LicenseType.PER_USER.value, total_seats=10,
        )
        SoftwareLicense.objects.create(
            organization=second_organization, software_name="Adobe",
            license_type=LicenseType.PER_DEVICE.value, total_seats=5,
        )
        response = org_admin_client.get("/api/v1/licenses/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_employee_can_list(self, employee_client, organization):
        """Employee can list licenses (read-only)."""
        SoftwareLicense.objects.create(
            organization=organization, software_name="Office",
            license_type=LicenseType.PER_USER.value, total_seats=10,
        )
        response = employee_client.get("/api/v1/licenses/")
        assert response.status_code == 200

    def test_unauthenticated_denied(self, api_client):
        response = api_client.get("/api/v1/licenses/")
        assert response.status_code == 401

    def test_org_admin_can_create(self, org_admin_client, organization):
        """Org admin can create a license."""
        response = create_license(org_admin_client, organization)
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["software_name"] == "Test Software"
        assert data["lic_id"].startswith("LIC")

    def test_employee_cannot_create(self, employee_client, organization):
        """Employee cannot create licenses."""
        response = create_license(employee_client, organization)
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Retrieve / Update / Delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLicenseRetrieveUpdateDelete:
    def test_can_retrieve_license(self, org_admin_client, organization):
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Office",
            license_type=LicenseType.PER_USER.value, total_seats=10,
        )
        response = org_admin_client.get(f"/api/v1/licenses/{lic.lic_id}/")
        assert response.status_code == 200
        assert response.json()["data"]["lic_id"] == lic.lic_id

    def test_can_partial_update_license(self, org_admin_client, organization):
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Office",
            license_type=LicenseType.PER_USER.value, total_seats=10,
        )
        response = org_admin_client.patch(
            f"/api/v1/licenses/{lic.lic_id}/",
            {"software_name": "Office 365"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["software_name"] == "Office 365"

    def test_can_delete_license(self, org_admin_client, organization):
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Office",
            license_type=LicenseType.PER_USER.value, total_seats=10,
        )
        response = org_admin_client.delete(f"/api/v1/licenses/{lic.lic_id}/")
        assert response.status_code == 204
        lic.refresh_from_db()
        assert lic.is_deleted is True

    def test_employee_cannot_update(self, employee_client, organization):
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Office",
            license_type=LicenseType.PER_USER.value, total_seats=10,
        )
        response = employee_client.patch(
            f"/api/v1/licenses/{lic.lic_id}/",
            {"software_name": "Hacked"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Assign
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLicenseAssign:
    def test_admin_can_assign_to_employee(
        self, org_admin_client, organization, employee
    ):
        """Org admin can assign a license to an employee."""
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Slack",
            license_type=LicenseType.PER_USER.value, total_seats=5,
        )
        response = org_admin_client.post(
            f"/api/v1/licenses/{lic.lic_id}/assign/",
            {"employee": str(employee.id)},
        )
        assert response.status_code == 201
        assert response.json()["data"]["employee"] == str(employee.id)

    def test_admin_can_assign_to_asset(
        self, org_admin_client, organization, asset
    ):
        """Org admin can assign a license to an asset."""
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Windows",
            license_type=LicenseType.PER_DEVICE.value, total_seats=5,
        )
        response = org_admin_client.post(
            f"/api/v1/licenses/{lic.lic_id}/assign/",
            {"asset": str(asset.id)},
        )
        assert response.status_code == 201
        assert response.json()["data"]["asset"] == str(asset.id)

    def test_cannot_assign_when_no_seats(
        self, org_admin_client, organization, employee
    ):
        """Cannot assign when all seats are taken."""
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Slack",
            license_type=LicenseType.PER_USER.value, total_seats=1,
        )
        LicenseAssignment.objects.create(
            organization=organization, license=lic, employee=employee
        )
        response = org_admin_client.post(
            f"/api/v1/licenses/{lic.lic_id}/assign/",
            {"employee": str(employee.id)},
        )
        assert response.status_code == 400

    def test_employee_cannot_assign(self, employee_client, organization, employee):
        """Employee cannot assign licenses."""
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Slack",
            license_type=LicenseType.PER_USER.value, total_seats=5,
        )
        response = employee_client.post(
            f"/api/v1/licenses/{lic.lic_id}/assign/",
            {"employee": str(employee.id)},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Revoke
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLicenseRevoke:
    def test_admin_can_revoke_assignment(
        self, org_admin_client, organization, employee
    ):
        """Org admin can revoke a license assignment."""
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Slack",
            license_type=LicenseType.PER_USER.value, total_seats=5,
        )
        a = LicenseAssignment.objects.create(
            organization=organization, license=lic, employee=employee
        )
        response = org_admin_client.post(
            f"/api/v1/licenses/{lic.lic_id}/revoke/",
            {"assignment_id": str(a.id)},
        )
        assert response.status_code == 200
        a.refresh_from_db()
        assert a.revoked_at is not None

    def test_cannot_revoke_already_revoked(
        self, org_admin_client, organization, employee
    ):
        """Cannot revoke an already-revoked assignment."""
        from django.utils import timezone

        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Slack",
            license_type=LicenseType.PER_USER.value, total_seats=5,
        )
        a = LicenseAssignment.objects.create(
            organization=organization, license=lic, employee=employee
        )
        a.revoked_at = timezone.now()
        a.save(update_fields=["revoked_at"])
        response = org_admin_client.post(
            f"/api/v1/licenses/{lic.lic_id}/revoke/",
            {"assignment_id": str(a.id)},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Utilization
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLicenseUtilization:
    def test_utilization_returns_stats(
        self, org_admin_client, organization, employee, asset
    ):
        """Utilization endpoint returns seat stats."""
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Slack",
            license_type=LicenseType.PER_USER.value, total_seats=10,
        )
        LicenseAssignment.objects.create(
            organization=organization, license=lic, employee=employee
        )
        LicenseAssignment.objects.create(
            organization=organization, license=lic, asset=asset
        )
        response = org_admin_client.get(
            f"/api/v1/licenses/{lic.lic_id}/utilization/"
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_seats"] == 10
        assert data["used_seats"] == 2
        assert data["available_seats"] == 8
        assert data["utilization_rate"] == 20.0


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLicenseFiltering:
    def test_filter_by_lic_id(self, org_admin_client, organization):
        """Filter licenses by license HRID."""
        l1 = SoftwareLicense.objects.create(
            organization=organization, software_name="Office",
            license_type=LicenseType.PER_USER.value, total_seats=10,
        )
        SoftwareLicense.objects.create(
            organization=organization, software_name="Adobe",
            license_type=LicenseType.PER_DEVICE.value, total_seats=5,
        )
        response = org_admin_client.get(
            f"/api/v1/licenses/?lic_id={l1.lic_id}"
        )
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_filter_by_license_type(self, org_admin_client, organization):
        """Filter licenses by type."""
        SoftwareLicense.objects.create(
            organization=organization, software_name="Office",
            license_type=LicenseType.PER_USER.value, total_seats=10,
        )
        SoftwareLicense.objects.create(
            organization=organization, software_name="Windows",
            license_type=LicenseType.PER_DEVICE.value, total_seats=5,
        )
        response = org_admin_client.get("/api/v1/licenses/?license_type=per_device")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLicenseEdgeCases:
    def test_cannot_assign_cross_org_employee(
        self, org_admin_client, organization, second_organization, asset
    ):
        """Cannot assign a license to an employee from a different org."""
        from django.contrib.auth import get_user_model
        from apps.core.employees.models import Employee

        User = get_user_model()
        other_user = User.objects.create_user(
            username="other_org_emp",
            email="other_org@test.com",
            password="testpass123",
            first_name="Other",
            last_name="Org",
            role="employee",
            organization_id=second_organization.id,
        )
        other_emp = Employee.objects.create(
            organization=second_organization,
            user=other_user,
            designation="Other Org",
        )
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Slack",
            license_type=LicenseType.PER_USER.value, total_seats=5,
        )
        response = org_admin_client.post(
            f"/api/v1/licenses/{lic.lic_id}/assign/",
            {"employee": str(other_emp.id)},
        )
        assert response.status_code == 400

    def test_cannot_assign_cross_org_asset(
        self, org_admin_client, organization, second_organization,
        employee, asset_category
    ):
        """Cannot assign a license to an asset from a different org."""
        from apps.assets.inventory.models import Asset

        other_asset = Asset.objects.create(
            organization=second_organization,
            category=asset_category,
            name="Other Asset",
        )
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Windows",
            license_type=LicenseType.PER_DEVICE.value, total_seats=5,
        )
        response = org_admin_client.post(
            f"/api/v1/licenses/{lic.lic_id}/assign/",
            {"asset": str(other_asset.id)},
        )
        assert response.status_code == 400

    def test_cannot_assign_without_target(self, org_admin_client, organization):
        """Cannot assign without employee or asset."""
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Slack",
            license_type=LicenseType.PER_USER.value, total_seats=5,
        )
        response = org_admin_client.post(
            f"/api/v1/licenses/{lic.lic_id}/assign/",
            {},
        )
        assert response.status_code == 400

    def test_can_assign_to_both_employee_and_asset(
        self, org_admin_client, organization, employee, asset
    ):
        """Can assign a license to both employee and asset."""
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Office",
            license_type=LicenseType.SITE.value, total_seats=5,
        )
        response = org_admin_client.post(
            f"/api/v1/licenses/{lic.lic_id}/assign/",
            {"employee": str(employee.id), "asset": str(asset.id)},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["employee"] == str(employee.id)
        assert data["asset"] == str(asset.id)

    def test_revoke_nonexistent_assignment(self, org_admin_client, organization):
        """Revoke with invalid assignment_id returns 404."""
        import uuid
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Slack",
            license_type=LicenseType.PER_USER.value, total_seats=5,
        )
        response = org_admin_client.post(
            f"/api/v1/licenses/{lic.lic_id}/revoke/",
            {"assignment_id": str(uuid.uuid4())},
        )
        assert response.status_code == 404

    def test_revoke_missing_assignment_id(self, org_admin_client, organization):
        """Revoke without assignment_id returns 400."""
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Slack",
            license_type=LicenseType.PER_USER.value, total_seats=5,
        )
        response = org_admin_client.post(
            f"/api/v1/licenses/{lic.lic_id}/revoke/",
            {},
        )
        assert response.status_code == 400

    def test_super_admin_can_create(self, super_admin_client, organization):
        """Super admin can create licenses."""
        response = create_license(super_admin_client, organization)
        if response.status_code != 201:
            print(response.json())
        assert response.status_code == 201

    def test_search_licenses(self, org_admin_client, organization):
        """Search licenses by software_name."""
        SoftwareLicense.objects.create(
            organization=organization, software_name="Microsoft Office",
            license_type=LicenseType.PER_USER.value, total_seats=10,
        )
        SoftwareLicense.objects.create(
            organization=organization, software_name="Adobe Photoshop",
            license_type=LicenseType.PER_DEVICE.value, total_seats=5,
        )
        response = org_admin_client.get("/api/v1/licenses/?search=Microsoft")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_list_assignments_for_license(
        self, org_admin_client, organization, employee, asset
    ):
        """GET /licenses/{id}/assignments/ lists all assignments."""
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Slack",
            license_type=LicenseType.PER_USER.value, total_seats=5,
        )
        LicenseAssignment.objects.create(
            organization=organization, license=lic, employee=employee
        )
        LicenseAssignment.objects.create(
            organization=organization, license=lic, asset=asset
        )
        response = org_admin_client.get(
            f"/api/v1/licenses/{lic.lic_id}/assignments/"
        )
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 2

    def test_utilization_zero_seats(self, org_admin_client, organization):
        """Utilization handles zero total_seats gracefully."""
        lic = SoftwareLicense.objects.create(
            organization=organization, software_name="Free Tool",
            license_type=LicenseType.SITE.value, total_seats=0,
        )
        response = org_admin_client.get(
            f"/api/v1/licenses/{lic.lic_id}/utilization/"
        )
        assert response.status_code == 200
        assert response.json()["data"]["utilization_rate"] == 0
