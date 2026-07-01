"""
apps/analytics/dashboard/tests.py — Tests for dashboard services and views.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.inventory.constants import AssetStatus
from apps.assets.inventory.models import Asset
from apps.assets.requests.constants import RequestPriority, RequestStatus
from apps.assets.requests.models import AssetRequest
from apps.core.employees.models import Department, Employee
from apps.operations.incidents.constants import IncidentCategory, IncidentStatus
from apps.operations.incidents.models import Incident
from apps.operations.licenses.constants import LicenseType
from apps.operations.licenses.models import LicenseAssignment, SoftwareLicense

from .services import (
    AllocationRepository,
    AssetRepository,
    DashboardSummaryService,
    IncidentRepository,
    LicenseRepository,
    RequestRepository,
)

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def org(db):
    from apps.core.organizations.models import Organization

    return Organization.objects.create(
        name="Test Org", slug="test-org", contact_email="admin@test.com"
    )


@pytest.fixture
def other_org(db):
    from apps.core.organizations.models import Organization

    return Organization.objects.create(
        name="Other Org", slug="other-org", contact_email="other@test.com"
    )


@pytest.fixture
def org_admin(db, org):
    from apps.core.users.models import User

    return User.objects.create_user(
        username="admin",
        email="admin@test.com",
        password="pass123",
        first_name="Org",
        last_name="Admin",
        organization=org,
        role="org_admin",
    )


@pytest.fixture
def super_admin(db):
    from apps.core.users.models import User

    return User.objects.create_user(
        username="super",
        email="super@test.com",
        password="pass123",
        first_name="Super",
        last_name="Admin",
        role="super_admin",
    )


@pytest.fixture
def employee_user(db, org):
    from apps.core.users.models import User

    return User.objects.create_user(
        username="emp",
        email="emp@test.com",
        password="pass123",
        first_name="Emp",
        last_name="Loyee",
        organization=org,
        role="employee",
    )


@pytest.fixture
def category(db, org):
    from apps.assets.categories.models import AssetCategory

    return AssetCategory.objects.create(organization=org, name="Electronics")


@pytest.fixture
def department(db, org):
    return Department.objects.create(organization=org, name="Engineering")


@pytest.fixture
def employee(db, org, department, org_admin):
    return Employee.objects.create(
        organization=org,
        user=org_admin,
        department=department,
        designation="Engineer",
    )


@pytest.fixture
def asset(db, org, category):
    return Asset.objects.create(
        organization=org,
        name="MacBook Pro",
        category=category,
        status=AssetStatus.AVAILABLE.value,
        serial_number="SN12345",
    )


@pytest.fixture
def allocated_asset(db, org, category):
    return Asset.objects.create(
        organization=org,
        name="Dell Monitor",
        category=category,
        status=AssetStatus.ALLOCATED.value,
        serial_number="SN67890",
    )


@pytest.fixture
def incident(db, org, asset, employee):
    return Incident.objects.create(
        organization=org,
        asset=asset,
        reported_by=employee,
        title="Broken screen",
        description="Screen cracked",
        category=IncidentCategory.PHYSICAL_DAMAGE.value,
        status=IncidentStatus.REPORTED.value,
    )


@pytest.fixture
def resolved_incident(db, org, asset, employee):
    return Incident.objects.create(
        organization=org,
        asset=asset,
        reported_by=employee,
        title="Fixed keyboard",
        description="Keyboard replaced",
        category=IncidentCategory.PHYSICAL_DAMAGE.value,
        status=IncidentStatus.RESOLVED.value,
    )


@pytest.fixture
def asset_request(db, org, category, employee):
    return AssetRequest.objects.create(
        organization=org,
        requested_by=employee,
        asset_category=category,
        reason="Need new laptop",
        priority=RequestPriority.HIGH.value,
        status=RequestStatus.PENDING.value,
    )


@pytest.fixture
def approved_request(db, org, category, employee):
    return AssetRequest.objects.create(
        organization=org,
        requested_by=employee,
        asset_category=category,
        reason="Need monitor",
        priority=RequestPriority.MEDIUM.value,
        status=RequestStatus.APPROVED.value,
    )


@pytest.fixture
def software_license(db, org):
    return SoftwareLicense.objects.create(
        organization=org,
        software_name="Microsoft Office",
        license_type=LicenseType.PER_USER.value,
        total_seats=10,
        vendor="Microsoft",
    )


@pytest.fixture
def license_assignment(db, software_license, employee):
    return LicenseAssignment.objects.create(
        organization=software_license.organization,
        license=software_license,
        employee=employee,
    )


@pytest.fixture
def allocation(db, org, asset, employee, org_admin):
    from apps.assets.allocations.models import Allocation

    return Allocation.objects.create(
        organization=org,
        asset=asset,
        employee=employee,
        allocated_by=org_admin,
    )


# ==============================================================================
# Service Tests
# ==============================================================================


class TestAssetRepository:
    def test_get_total_count(self, org, asset, allocated_asset):
        assert AssetRepository.get_total_count(org) == 2

    def test_get_status_breakdown(self, org, asset, allocated_asset):
        breakdown = AssetRepository.get_status_breakdown(org)
        status_map = {b["status"]: b["count"] for b in breakdown}
        assert status_map[AssetStatus.AVAILABLE.value] == 1
        assert status_map[AssetStatus.ALLOCATED.value] == 1

    def test_get_category_breakdown(self, org, asset, category):
        breakdown = AssetRepository.get_category_breakdown(org)
        assert len(breakdown) == 1
        assert breakdown[0]["name"] == category.name
        assert breakdown[0]["count"] == 1

    def test_utilization_rate(self, org, asset):
        # Only 1 available asset — 0% utilization
        assert AssetRepository.get_utilization_rate(org) == 0.0

    def test_utilization_rate_with_allocated(self, org, asset, allocated_asset):
        # 1 allocated out of 2
        assert AssetRepository.get_utilization_rate(org) == 50.0

    def test_org_scoped(self, org, other_org, asset):
        """Assets in other_org are not counted."""
        Asset.objects.create(
            organization=other_org,
            name="Other Asset",
            status=AssetStatus.AVAILABLE.value,
        )
        assert AssetRepository.get_total_count(org) == 1
        assert AssetRepository.get_total_count(other_org) == 1


class TestIncidentRepository:
    def test_get_total_count(self, org, incident, resolved_incident):
        assert IncidentRepository.get_total_count(org) == 2

    def test_get_status_breakdown(self, org, incident, resolved_incident):
        breakdown = IncidentRepository.get_status_breakdown(org)
        status_map = {b["status"]: b["count"] for b in breakdown}
        assert status_map[IncidentStatus.REPORTED.value] == 1
        assert status_map[IncidentStatus.RESOLVED.value] == 1

    def test_open_count(self, org, incident, resolved_incident):
        # Only the "reported" one is open
        assert IncidentRepository.get_open_count(org) == 1

    def test_resolved_count(self, org, incident, resolved_incident):
        assert IncidentRepository.get_resolved_count(org) == 1


class TestRequestRepository:
    def test_get_total_count(self, org, asset_request, approved_request):
        assert RequestRepository.get_total_count(org) == 2

    def test_get_status_breakdown(self, org, asset_request, approved_request):
        breakdown = RequestRepository.get_status_breakdown(org)
        status_map = {b["status"]: b["count"] for b in breakdown}
        assert status_map[RequestStatus.PENDING.value] == 1
        assert status_map[RequestStatus.APPROVED.value] == 1

    def test_pending_count(self, org, asset_request, approved_request):
        assert RequestRepository.get_pending_count(org) == 1
        assert RequestRepository.get_approved_count(org) == 1
        assert RequestRepository.get_rejected_count(org) == 0


class TestLicenseRepository:
    def test_get_total_count(self, org, software_license):
        assert LicenseRepository.get_total_count(org) == 1

    def test_get_total_seats(self, org, software_license):
        assert LicenseRepository.get_total_seats(org) == 10

    def test_get_used_seats(self, org, software_license, license_assignment):
        assert LicenseRepository.get_used_seats(org) == 1

    def test_utilization_rate(self, org, software_license, license_assignment):
        assert LicenseRepository.get_license_utilization_rate(org) == 10.0

    def test_empty_org_utilization(self, org):
        """No licenses → 0% utilization, no crash."""
        assert LicenseRepository.get_license_utilization_rate(org) == 0.0


class TestAllocationRepository:
    def test_get_total_count(self, org, allocation):
        assert AllocationRepository.get_total_count(org) == 1

    def test_active_count(self, org, allocation):
        assert AllocationRepository.get_active_count(org) == 1

    def test_returned_count(self, org, allocation):
        assert AllocationRepository.get_returned_count(org) == 0


class TestDashboardSummaryService:
    def test_get_summary(self, org, asset, incident, asset_request, software_license, allocation):
        summary = DashboardSummaryService.get_summary(org)
        assert "assets" in summary
        assert "incidents" in summary
        assert "requests" in summary
        assert "licenses" in summary
        assert "allocations" in summary
        assert "employees" in summary

    def test_summary_counts(self, org, asset, allocated_asset, incident, resolved_incident):
        summary = DashboardSummaryService.get_summary(org)
        assert summary["assets"]["total"] == 2
        assert summary["assets"]["utilization_rate"] == 50.0
        assert summary["incidents"]["total"] == 2
        assert summary["incidents"]["open"] == 1

    def test_org_scoped_summary(self, org, other_org, asset):
        """Other org's data doesn't leak into summary."""
        Asset.objects.create(
            organization=other_org,
            name="Other Asset",
            status=AssetStatus.ALLOCATED.value,
        )
        summary = DashboardSummaryService.get_summary(org)
        assert summary["assets"]["total"] == 1


# ==============================================================================
# View Tests
# ==============================================================================


class TestDashboardSummaryView:
    url = reverse("dashboard-summary")

    def test_requires_auth(self):
        resp = APIClient().get(self.url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_summary(self, org, org_admin, asset, incident):
        client = APIClient()
        client.force_authenticate(user=org_admin)
        resp = client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["success"] is True
        data = resp.data["data"]
        assert "assets" in data

    def test_super_admin_can_query_other_org(self, org, other_org, super_admin, asset):
        """Super admin passes ?organization_id= to see other org."""
        Asset.objects.create(
            organization=other_org,
            name="Other Asset",
            status=AssetStatus.AVAILABLE.value,
        )
        client = APIClient()
        client.force_authenticate(user=super_admin)
        resp = client.get(self.url, {"organization_id": str(other_org.pk)})
        assert resp.status_code == status.HTTP_200_OK
        # Should see only other_org's asset
        assert resp.data["data"]["assets"]["total"] == 1

    def test_org_scoped(self, org, other_org, org_admin, asset):
        """Regular admin only sees their own org."""
        Asset.objects.create(
            organization=other_org,
            name="Other Asset",
            status=AssetStatus.AVAILABLE.value,
        )
        client = APIClient()
        client.force_authenticate(user=org_admin)
        resp = client.get(self.url)
        assert resp.data["data"]["assets"]["total"] == 1

    def test_employee_can_access(self, employee_user):
        """Employees can also view the dashboard."""
        client = APIClient()
        client.force_authenticate(user=employee_user)
        resp = client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK

    def test_user_without_org_gets_400(self, db):
        from apps.core.users.models import User

        orphan = User.objects.create_user(
            username="orphan",
            email="orphan@test.com",
            password="pass123",
            role="employee",
            organization=None,
        )
        client = APIClient()
        client.force_authenticate(user=orphan)
        resp = client.get(self.url)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestAssetDashboardView:
    url = reverse("dashboard-assets")

    def test_requires_auth(self):
        resp = APIClient().get(self.url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_asset_stats(self, org, org_admin, asset, category, allocated_asset):
        client = APIClient()
        client.force_authenticate(user=org_admin)
        resp = client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["total_assets"] == 2
        assert len(data["status_breakdown"]) == 2
        assert len(data["category_breakdown"]) == 1
        assert data["utilization_rate"] == 50.0


class TestIncidentDashboardView:
    url = reverse("dashboard-incidents")

    def test_returns_incident_stats(self, org, org_admin, incident, resolved_incident):
        client = APIClient()
        client.force_authenticate(user=org_admin)
        resp = client.get(self.url)
        assert resp.status_code == 200
        data = resp.data["data"]
        assert data["total_incidents"] == 2
        assert len(data["status_breakdown"]) == 2


class TestRequestDashboardView:
    url = reverse("dashboard-requests")

    def test_returns_request_stats(self, org, org_admin, asset_request, approved_request):
        client = APIClient()
        client.force_authenticate(user=org_admin)
        resp = client.get(self.url)
        assert resp.status_code == 200
        data = resp.data["data"]
        assert data["total_requests"] == 2
        assert len(data["status_breakdown"]) == 2


class TestLicenseDashboardView:
    url = reverse("dashboard-licenses")

    def test_returns_license_stats(self, org, org_admin, software_license, license_assignment):
        client = APIClient()
        client.force_authenticate(user=org_admin)
        resp = client.get(self.url)
        assert resp.status_code == 200
        data = resp.data["data"]
        assert data["total_licenses"] == 1
        assert data["total_seats"] == 10
        assert data["used_seats"] == 1
        assert data["utilization_rate"] == 10.0


class TestAllocationDashboardView:
    url = reverse("dashboard-allocations")

    def test_returns_allocation_stats(self, org, org_admin, allocation):
        client = APIClient()
        client.force_authenticate(user=org_admin)
        resp = client.get(self.url)
        assert resp.status_code == 200
        data = resp.data["data"]
        assert data["total_allocations"] == 1
        assert data["active"] == 1
        assert data["returned"] == 0


# ==============================================================================
# Visualization Tests
# ==============================================================================


class TestVisualizationViews:
    def test_summary_json_has_visualization_url(self, org, org_admin):
        """JSON summary endpoint includes visualization_url."""
        client = APIClient()
        client.force_authenticate(user=org_admin)
        resp = client.get(reverse("dashboard-summary"))
        assert resp.status_code == 200
        assert "visualization_url" in resp.data["data"]

    def test_assets_html_renders(self, org, org_admin):
        """Asset visualization page renders HTML with Chart.js."""
        client = APIClient()
        client.force_authenticate(user=org_admin)
        resp = client.get(reverse("dashboard-assets-visualize"))
        assert resp.status_code == 200
        assert resp["content-type"].startswith("text/html")
        assert b"chart.min.js" in resp.content
        assert b"Asset Dashboard" in resp.content

    def test_summary_html_renders(self, org, org_admin):
        """Summary visualization page renders with Chart.js."""
        client = APIClient()
        client.force_authenticate(user=org_admin)
        resp = client.get(reverse("dashboard-summary-visualize"))
        assert resp.status_code == 200
        assert resp["content-type"].startswith("text/html")
        assert b"Organization Summary" in resp.content

    def test_incidents_html_renders(self, org, org_admin):
        client = APIClient()
        client.force_authenticate(user=org_admin)
        resp = client.get(reverse("dashboard-incidents-visualize"))
        assert resp.status_code == 200
        assert b"chart.min.js" in resp.content
        assert b"Incident Dashboard" in resp.content

    def test_requests_html_renders(self, org, org_admin):
        client = APIClient()
        client.force_authenticate(user=org_admin)
        resp = client.get(reverse("dashboard-requests-visualize"))
        assert resp.status_code == 200
        assert b"chart.min.js" in resp.content
        assert b"Request Dashboard" in resp.content

    def test_licenses_html_renders(self, org, org_admin):
        client = APIClient()
        client.force_authenticate(user=org_admin)
        resp = client.get(reverse("dashboard-licenses-visualize"))
        assert resp.status_code == 200
        assert b"chart.min.js" in resp.content
        assert b"License Dashboard" in resp.content

    def test_allocations_html_renders(self, org, org_admin):
        client = APIClient()
        client.force_authenticate(user=org_admin)
        resp = client.get(reverse("dashboard-allocations-visualize"))
        assert resp.status_code == 200
        assert b"chart.min.js" in resp.content
        assert b"Allocation Dashboard" in resp.content

    def test_visualize_requires_auth(self):
        """Unauthenticated users cannot access visualization pages."""
        client = APIClient()
        resp = client.get(reverse("dashboard-assets-visualize"))
        assert resp.status_code in [401, 403]
