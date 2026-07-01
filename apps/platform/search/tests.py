"""
apps/platform/search/tests.py — Tests for the Global Search endpoint.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.assets.inventory.constants import AssetStatus
from apps.assets.inventory.models import Asset
from apps.assets.requests.constants import RequestPriority, RequestStatus
from apps.assets.requests.models import AssetRequest
from apps.core.employees.models import Department, Employee
from apps.operations.incidents.constants import IncidentCategory, IncidentStatus
from apps.operations.incidents.models import Incident
from apps.operations.licenses.constants import LicenseType
from apps.operations.licenses.models import SoftwareLicense


class GlobalSearchTests(APITestCase):
    """Tests for GlobalSearchView."""

    @classmethod
    def setUpTestData(cls):
        from apps.core.organizations.models import Organization
        from apps.core.users.models import User
        from apps.assets.categories.models import AssetCategory

        cls.org = Organization.objects.create(
            name="Test Org", slug="test-org", contact_email="admin@test.com"
        )
        cls.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="pass123",
            first_name="Org",
            last_name="Admin",
            organization=cls.org,
            role="org_admin",
        )
        cls.category = AssetCategory.objects.create(
            organization=cls.org, name="Electronics"
        )
        cls.department = Department.objects.create(
            organization=cls.org, name="Engineering"
        )
        cls.employee = Employee.objects.create(
            organization=cls.org,
            user=cls.admin,
            department=cls.department,
            designation="Engineer",
        )
        cls.asset = Asset.objects.create(
            organization=cls.org,
            name="MacBook Pro",
            category=cls.category,
            status=AssetStatus.AVAILABLE.value,
            serial_number="SN12345",
        )
        cls.incident = Incident.objects.create(
            organization=cls.org,
            asset=cls.asset,
            reported_by=cls.employee,
            title="Broken screen",
            description="Screen cracked on MacBook Pro",
            category=IncidentCategory.PHYSICAL_DAMAGE.value,
        )
        cls.software_license = SoftwareLicense.objects.create(
            organization=cls.org,
            software_name="Microsoft Office",
            license_type=LicenseType.PER_USER.value,
            total_seats=10,
            vendor="Microsoft",
        )
        cls.asset_request = AssetRequest.objects.create(
            organization=cls.org,
            requested_by=cls.employee,
            asset_category=cls.category,
            reason="Need new laptop",
            priority=RequestPriority.HIGH.value,
            status=RequestStatus.PENDING.value,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("global-search")

    def test_search_requires_q_param(self):
        """GET without q param returns 400."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_search_requires_auth(self):
        """Unauthenticated request gets 401."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url, {"q": "MacBook"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_assets(self):
        """Search finds assets by name."""
        response = self.client.get(self.url, {"q": "MacBook"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assets_result = next(r for r in response.data["data"]["results"] if r["type"] == "assets")
        self.assertEqual(assets_result["count"], 1)
        self.assertEqual(assets_result["results"][0]["name"], "MacBook Pro")

    def test_search_employees(self):
        """Search finds employees by name."""
        response = self.client.get(self.url, {"q": "Org"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emp_result = next(r for r in response.data["data"]["results"] if r["type"] == "employees")
        self.assertEqual(emp_result["count"], 1)

    def test_search_incidents(self):
        """Search finds incidents by title."""
        response = self.client.get(self.url, {"q": "Broken"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        inc_result = next(r for r in response.data["data"]["results"] if r["type"] == "incidents")
        self.assertEqual(inc_result["count"], 1)
        self.assertEqual(inc_result["results"][0]["title"], "Broken screen")

    def test_search_licenses(self):
        """Search finds licenses by software name."""
        response = self.client.get(self.url, {"q": "Microsoft"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lic_result = next(r for r in response.data["data"]["results"] if r["type"] == "licenses")
        self.assertEqual(lic_result["count"], 1)
        self.assertEqual(lic_result["results"][0]["software_name"], "Microsoft Office")

    def test_search_requests(self):
        """Search finds requests by reason."""
        response = self.client.get(self.url, {"q": "laptop"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        req_result = next(r for r in response.data["data"]["results"] if r["type"] == "requests")
        self.assertEqual(req_result["count"], 1)

    def test_search_type_filter(self):
        """?type=assets returns only assets."""
        response = self.client.get(self.url, {"q": "MacBook", "type": "assets"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_types = [r["type"] for r in response.data["data"]["results"]]
        self.assertEqual(result_types, ["assets"])

    def test_search_type_filter_multiple(self):
        """?type=assets,incidents returns only those types."""
        response = self.client.get(self.url, {"q": "MacBook", "type": "assets,incidents"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_types = [r["type"] for r in response.data["data"]["results"]]
        self.assertEqual(result_types, ["assets", "incidents"])

    def test_search_no_matches(self):
        """Search with no matches returns zero counts."""
        response = self.client.get(self.url, {"q": "xyznonexistent123"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for result in response.data["data"]["results"]:
            self.assertEqual(result["count"], 0)
            self.assertEqual(result["results"], [])

    def test_search_org_scoped(self):
        """Non-super-admin sees only their org's data."""
        other_org = self.__class__.org.__class__.objects.create(
            name="Other Org", slug="other-org", contact_email="other@test.com"
        )
        # Create matching data in other org — should not appear
        Asset.objects.create(
            organization=other_org,
            name="MacBook Pro",
            category=self.__class__.category,
            status=AssetStatus.AVAILABLE.value,
        )
        response = self.client.get(self.url, {"q": "MacBook"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assets_result = next(r for r in response.data["data"]["results"] if r["type"] == "assets")
        self.assertEqual(assets_result["count"], 1)  # only our org's asset

    def test_search_response_shape(self):
        """Response has the expected structure."""
        response = self.client.get(self.url, {"q": "MacBook"})
        self.assertIn("success", response.data)
        self.assertIn("data", response.data)
        self.assertIn("query", response.data["data"])
        self.assertIn("results", response.data["data"])
        for result in response.data["data"]["results"]:
            self.assertIn("type", result)
            self.assertIn("label", result)
            self.assertIn("count", result)
            self.assertIn("results", result)
            self.assertIn("view_all_url", result)

    def test_search_view_all_url(self):
        """view_all_url points to the per-app search endpoint."""
        response = self.client.get(self.url, {"q": "MacBook"})
        assets_result = next(r for r in response.data["data"]["results"] if r["type"] == "assets")
        self.assertIn("search=MacBook", assets_result["view_all_url"])
