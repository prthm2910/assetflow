"""tests/integration/test_asset_lifecycle.py — Full app flow integration tests.

Tests the complete lifecycle: org → user → employee → department → category
→ asset → allocation → request → incident → license.
"""

import pytest

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.base.constants import UserRole
from apps.assets.inventory.constants import AssetStatus
from apps.assets.requests.constants import RequestPriority, RequestStatus
from apps.operations.incidents.constants import IncidentStatus, IncidentCategory
from apps.operations.licenses.constants import LicenseType
from apps.core.organizations.models import Organization
from apps.core.employees.models import Department, Employee
from apps.assets.categories.models import AssetCategory
from apps.assets.inventory.models import Asset
from apps.assets.allocations.models import Allocation
from apps.assets.requests.models import AssetRequest
from apps.operations.incidents.models import Incident
from apps.operations.licenses.models import SoftwareLicense, LicenseAssignment


User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures for integration tests
# ---------------------------------------------------------------------------


@pytest.fixture
def org_admin_user_obj(transactional_db):
    """Create org with org admin user and employee profile."""
    org = Organization.objects.create(
        name="Integration Test Org",
        slug="integration-test-org",
        contact_email="admin@integration.com",
    )
    admin_user = User.objects.create_user(
        username="org_admin_int",
        email="org_admin@integration.com",
        password="testpass123",
        first_name="Org",
        last_name="Admin",
        role=UserRole.ORG_ADMIN.value,
        organization_id=org.id,
    )
    dept = Department.objects.create(
        organization=org,
        name="Engineering",
        code="ENG",
    )
    admin_emp = Employee.objects.create(
        organization=org,
        user=admin_user,
        department=dept,
        designation="Engineering Manager",
    )
    return {
        "org": org,
        "admin_user": admin_user,
        "admin_emp": admin_emp,
        "dept": dept,
    }


@pytest.fixture
def employee_user_obj(transactional_db, org_admin_user_obj):
    """Create a regular employee in the same org."""
    org = org_admin_user_obj["org"]
    dept = org_admin_user_obj["dept"]
    emp_user = User.objects.create_user(
        username="emp_int",
        email="employee@integration.com",
        password="testpass123",
        first_name="Test",
        last_name="Employee",
        role=UserRole.EMPLOYEE.value,
        organization_id=org.id,
    )
    emp = Employee.objects.create(
        organization=org,
        user=emp_user,
        department=dept,
        designation="Software Engineer",
    )
    return {"user": emp_user, "employee": emp}


@pytest.fixture
def api_clients(transactional_db, org_admin_user_obj, employee_user_obj):
    """Return authenticated API clients."""
    from rest_framework.test import APIClient

    admin_client = APIClient()
    admin_client.force_authenticate(user=org_admin_user_obj["admin_user"])

    emp_client = APIClient()
    emp_client.force_authenticate(user=employee_user_obj["user"])

    return {
        "admin": admin_client,
        "employee": emp_client,
    }


@pytest.fixture
def asset_cat(transactional_db, org_admin_user_obj):
    """Create an asset category."""
    return AssetCategory.objects.create(
        organization=org_admin_user_obj["org"],
        name="Laptops",
        description="Development laptops",
    )


@pytest.fixture
def asset_obj(transactional_db, org_admin_user_obj, asset_cat):
    """Create an asset."""
    return Asset.objects.create(
        organization=org_admin_user_obj["org"],
        category=asset_cat,
        name="MacBook Pro 16",
        description="Development laptop",
    )


# ---------------------------------------------------------------------------
# Test: Full asset lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFullAssetLifecycle:
    """
    Test the complete flow:
    1. Admin creates asset
    2. Employee requests asset
    3. Admin approves request
    4. Admin allocates asset to employee
    5. Employee reports incident on asset
    6. Admin assigns, resolves, closes incident
    7. Admin assigns software license to employee + asset
    8. Admin revokes license
    """

    def test_end_to_end_flow(
        self, org_admin_user_obj, employee_user_obj,
        api_clients, asset_cat, asset_obj
    ):
        admin = api_clients["admin"]
        emp = api_clients["employee"]
        org = org_admin_user_obj["org"]
        admin_emp = org_admin_user_obj["admin_emp"]
        employee = employee_user_obj["employee"]
        asset = asset_obj

        # --- Step 1: Asset starts as available ---
        assert asset.status == AssetStatus.AVAILABLE.value

        # --- Step 2: Employee submits asset request ---
        response = emp.post(
            "/api/v1/assets/requests/submit/",
            {
                "asset_category": str(asset_cat.id),
                "reason": "Need laptop for development",
            },
        )
        assert response.status_code == 201
        req_data = response.json()["data"]
        assert req_data["status"] == RequestStatus.PENDING.value
        req_id = req_data["req_id"]

        # --- Step 3: Admin approves request ---
        response = admin.post(
            f"/api/v1/assets/requests/{req_id}/approve/",
            {"review_notes": "Approved for new hire."},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == RequestStatus.APPROVED.value

        # --- Step 4: Admin allocates asset to employee ---

        response = admin.post(
            "/api/v1/assets/allocations/",
            {
                "asset": str(asset.id),
                "employee": str(employee.id),
            },
        )
        assert response.status_code == 201
        alloc_data = response.json()["data"]
        assert alloc_data["is_current"] is True

        asset.refresh_from_db()
        assert asset.status == AssetStatus.ALLOCATED.value

        # --- Step 5: Employee reports incident on asset ---
        response = emp.post(
            "/api/v1/incidents/report/",
            {
                "asset": str(asset.id),
                "title": "Keyboard malfunction",
                "description": "Several keys are unresponsive.",
                "category": IncidentCategory.HARDWARE.value,
            },
        )
        assert response.status_code == 201
        inc_data = response.json()["data"]
        assert inc_data["status"] == IncidentStatus.REPORTED.value
        inc_id = inc_data["inc_id"]

        # --- Step 6: Admin assigns incident ---
        response = admin.post(
            f"/api/v1/incidents/{inc_id}/assign/",
            {"assigned_to": str(admin_emp.id)},
        )
        if response.status_code != 200:
            print(response.json())
        assert response.status_code == 200
        assert response.json()["data"]["status"] == IncidentStatus.OPEN.value

        # Admin starts work (transitions open → in_progress)
        response = admin.post(
            f"/api/v1/incidents/{inc_id}/start/",
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == IncidentStatus.IN_PROGRESS.value

        # Admin resolves
        response = admin.post(
            f"/api/v1/incidents/{inc_id}/resolve/",
            {"resolution_notes": "Replaced keyboard module."},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == IncidentStatus.RESOLVED.value

        # Admin closes
        response = admin.post(
            f"/api/v1/incidents/{inc_id}/close/",
            {"close_notes": "Verified with employee."},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == IncidentStatus.CLOSED.value

        # --- Step 7: Admin assigns software license to employee + asset ---
        lic_response = admin.post(
            "/api/v1/licenses/",
            {
                "software_name": "JetBrains IntelliJ",
                "license_type": LicenseType.PER_USER.value,
                "total_seats": 5,
                "organization": str(org.id),
            },
        )
        assert lic_response.status_code == 201
        lic_id = lic_response.json()["data"]["lic_id"]

        # Assign to employee
        assign_response = admin.post(
            f"/api/v1/licenses/{lic_id}/assign/",
            {"employee": str(employee.id)},
        )
        assert assign_response.status_code == 201

        # Verify utilization
        util_response = admin.get(f"/api/v1/licenses/{lic_id}/utilization/")
        assert util_response.status_code == 200
        util_data = util_response.json()["data"]
        assert util_data["used_seats"] == 1
        assert util_data["available_seats"] == 4

        # --- Step 8: Admin revokes license ---
        assignment_id = assign_response.json()["data"]["id"]
        revoke_response = admin.post(
            f"/api/v1/licenses/{lic_id}/revoke/",
            {"assignment_id": str(assignment_id)},
        )
        assert revoke_response.status_code == 200

        # Verify utilization after revoke
        util_response = admin.get(f"/api/v1/licenses/{lic_id}/utilization/")
        assert util_response.json()["data"]["used_seats"] == 0
        assert util_response.json()["data"]["available_seats"] == 5

        # --- Verify: Employee can see their own incident and request ---
        emp_incidents = emp.get("/api/v1/incidents/")
        assert emp_incidents.status_code == 200
        assert emp_incidents.json()["data"]["count"] == 1

        emp_requests = emp.get("/api/v1/assets/requests/")
        assert emp_requests.status_code == 200
        assert emp_requests.json()["data"]["count"] == 1
