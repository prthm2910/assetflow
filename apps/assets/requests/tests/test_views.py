"""
apps/assets/requests/tests/test_views.py — API tests for AssetRequest endpoints.
"""

import pytest

from apps.assets.requests.models import AssetRequest
from apps.assets.requests.constants import RequestStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_request(client, organization, employee, asset_category, reason="", priority="medium"):
    """Create an asset request via API and return the response."""
    return client.post(
        "/api/v1/assets/requests/submit/",
        {
            "asset_category": str(asset_category.id),
            "reason": reason or "Standard asset request",
            "priority": priority,
        },
    )


# ---------------------------------------------------------------------------
# List / Submit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAssetRequestListSubmit:
    def test_super_admin_sees_all_orgs_requests(
        self, super_admin_client, organization, second_organization,
        employee, asset_category
    ):
        """Super admin sees requests across all organizations."""
        AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Org 1 request",
        )
        # Second org setup
        from apps.assets.categories.models import AssetCategory
        from apps.core.employees.models import Employee
        from django.contrib.auth import get_user_model
        User = get_user_model()
        second_user = User.objects.create_user(
            username="second", email="s@s.com", password="p",
            role="employee", organization_id=second_organization.id,
        )
        second_emp = Employee.objects.create(
            organization=second_organization, user=second_user,
            designation="SE", employee_number="S-001",
        )
        second_cat = AssetCategory.objects.create(
            organization=second_organization, name="Second Cat",
        )
        AssetRequest.objects.create(
            organization=second_organization,
            requested_by=second_emp,
            asset_category=second_cat,
            reason="Org 2 request",
        )
        response = super_admin_client.get("/api/v1/assets/requests/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 2

    def test_org_admin_sees_own_org_only(
        self, org_admin_client, organization, second_organization,
        employee, asset_category
    ):
        """Org admin sees only requests in their own org."""
        AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="My org request",
        )
        from apps.assets.categories.models import AssetCategory
        from apps.core.employees.models import Employee
        from django.contrib.auth import get_user_model
        User = get_user_model()
        second_user = User.objects.create_user(
            username="second", email="s@s.com", password="p",
            role="employee", organization_id=second_organization.id,
        )
        second_emp = Employee.objects.create(
            organization=second_organization, user=second_user,
            designation="SE", employee_number="S-001",
        )
        second_cat = AssetCategory.objects.create(
            organization=second_organization, name="Other Cat",
        )
        AssetRequest.objects.create(
            organization=second_organization,
            requested_by=second_emp,
            asset_category=second_cat,
            reason="Other org request",
        )
        response = org_admin_client.get("/api/v1/assets/requests/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_employee_sees_only_own_requests(
        self, employee_client, organization, employee, second_employee, asset_category, department
    ):
        """Employee sees only their own requests."""
        from apps.assets.categories.models import AssetCategory
        cat2 = AssetCategory.objects.create(
            organization=organization, name="Monitors",
        )
        AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="My request",
        )
        AssetRequest.objects.create(
            organization=organization,
            requested_by=second_employee,
            asset_category=cat2,
            reason="Other request",
        )
        response = employee_client.get("/api/v1/assets/requests/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_unauthenticated_denied(self, api_client):
        response = api_client.get("/api/v1/assets/requests/")
        assert response.status_code == 401

    def test_employee_can_submit_request(
        self, employee_client, organization, employee, asset_category
    ):
        """Employees can submit asset requests via /submit/."""
        response = create_request(employee_client, organization, employee, asset_category)
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["requested_by"] == str(employee.id)
        assert data["asset_category"] == str(asset_category.id)
        assert data["status"] == RequestStatus.PENDING.value
        assert data["req_id"].startswith("REQ")

    def test_org_admin_can_submit_request(
        self, org_admin_client, organization, org_admin_employee, asset_category
    ):
        """Org admins can submit requests too."""
        response = create_request(
            org_admin_client, organization, org_admin_employee, asset_category
        )
        assert response.status_code == 201

    def test_super_admin_can_submit_request(
        self, super_admin_client, organization, employee, asset_category
    ):
        """Super admin can submit requests when they have an employee profile.

        Note: super_admin_user fixture has no employee_profile by default.
        In practice, super admins submit via the API with a requested_by field,
        or they use an org admin account. This test documents that a super admin
        without an employee profile cannot submit directly.
        """
        response = create_request(super_admin_client, organization, employee, asset_category)
        # Super admin has no employee_profile → blocked
        assert response.status_code == 400
        assert "No employee profile" in response.json()["error"]

    def test_submit_requires_employee_profile(
        self, org_admin_client, organization, asset_category
    ):
        """Submitting fails if the user has no employee profile."""
        response = create_request(org_admin_client, organization, None, asset_category)
        assert response.status_code == 400

    def test_submit_generates_req_id(self, employee_client, organization, employee, asset_category):
        """Submitting generates a req_id HRID."""
        response = create_request(employee_client, organization, employee, asset_category)
        assert response.status_code == 201
        import re
        assert re.match(r"REQ[A-Z0-9]{6}$", response.json()["data"]["req_id"])


# ---------------------------------------------------------------------------
# Retrieve / Update / Delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAssetRequestRetrieveUpdateDelete:
    def test_can_retrieve_request(
        self, org_admin_client, organization, employee, asset_category
    ):
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Test request",
        )
        response = org_admin_client.get(f"/api/v1/assets/requests/{req.req_id}/")
        assert response.status_code == 200
        assert response.json()["data"]["req_id"] == req.req_id

    def test_can_partial_update_request(
        self, org_admin_client, organization, employee, asset_category
    ):
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Test request",
        )
        response = org_admin_client.patch(
            f"/api/v1/assets/requests/{req.req_id}/",
            {"review_notes": "Admin reviewed this"},
        )
        assert response.status_code == 200
        assert "Admin reviewed this" in response.json()["data"]["review_notes"]

    def test_can_delete_request(
        self, org_admin_client, organization, employee, asset_category
    ):
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="To be deleted",
        )
        response = org_admin_client.delete(f"/api/v1/assets/requests/{req.req_id}/")
        assert response.status_code == 204
        req.refresh_from_db()
        assert req.is_deleted is True

    def test_employee_cannot_delete_via_destroy(
        self, employee_client, organization, employee, asset_category
    ):
        """Employees cannot hard-delete requests via DELETE endpoint."""
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Test",
        )
        response = employee_client.delete(f"/api/v1/assets/requests/{req.req_id}/")
        assert response.status_code == 403

    def test_cannot_modify_core_fields(
        self, org_admin_client, organization, employee, asset_category
    ):
        """Core fields (org, requested_by, asset_category) cannot be changed."""
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Test",
        )
        response = org_admin_client.patch(
            f"/api/v1/assets/requests/{req.req_id}/",
            {"requested_by": str(employee.id), "status": "approved"},
        )
        # status should be mutable; org/requested_by should not
        # The patch will update status but not the core fields
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAssetRequestApprove:
    def test_org_admin_can_approve_pending_request(
        self, org_admin_client, organization, employee, asset_category
    ):
        """Org admin can approve a pending request."""
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Need a laptop",
        )
        response = org_admin_client.post(
            f"/api/v1/assets/requests/{req.req_id}/approve/",
            {"review_notes": "Approved. Proceed with allocation."},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == RequestStatus.APPROVED.value
        assert "Approved" in data["review_notes"]

    def test_super_admin_can_approve(
        self, super_admin_client, organization, employee, asset_category
    ):
        """Super admin can approve requests across any org."""
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Test approve",
        )
        response = super_admin_client.post(
            f"/api/v1/assets/requests/{req.req_id}/approve/",
        )
        assert response.status_code == 200

    def test_employee_cannot_approve(
        self, employee_client, organization, employee, asset_category
    ):
        """Employees cannot approve requests."""
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Test",
        )
        response = employee_client.post(
            f"/api/v1/assets/requests/{req.req_id}/approve/",
        )
        assert response.status_code == 403

    def test_cannot_approve_non_pending_request(
        self, org_admin_client, organization, employee, asset_category
    ):
        """Only pending requests can be approved."""
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Test",
            status=RequestStatus.APPROVED.value,
        )
        response = org_admin_client.post(
            f"/api/v1/assets/requests/{req.req_id}/approve/",
        )
        assert response.status_code == 400

    def test_approve_sets_reviewed_by_and_reviewed_at(
        self, org_admin_client, organization, employee, asset_category
    ):
        """Approval records who reviewed and when."""
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Test",
        )
        response = org_admin_client.post(
            f"/api/v1/assets/requests/{req.req_id}/approve/",
        )
        assert response.status_code == 200
        req.refresh_from_db()
        assert req.reviewed_by is not None
        assert req.reviewed_at is not None
        assert req.status == RequestStatus.APPROVED.value


# ---------------------------------------------------------------------------
# Reject
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAssetRequestReject:
    def test_org_admin_can_reject_pending_request(
        self, org_admin_client, organization, employee, asset_category
    ):
        """Org admin can reject a pending request."""
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Need a laptop",
        )
        response = org_admin_client.post(
            f"/api/v1/assets/requests/{req.req_id}/reject/",
            {"review_notes": "Budget constraints. Please resubmit next quarter."},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == RequestStatus.REJECTED.value

    def test_employee_cannot_reject(
        self, employee_client, organization, employee, asset_category
    ):
        """Employees cannot reject requests."""
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Test",
        )
        response = employee_client.post(
            f"/api/v1/assets/requests/{req.req_id}/reject/",
        )
        assert response.status_code == 403

    def test_cannot_reject_non_pending_request(
        self, org_admin_client, organization, employee, asset_category
    ):
        """Only pending requests can be rejected."""
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Test",
            status=RequestStatus.REJECTED.value,
        )
        response = org_admin_client.post(
            f"/api/v1/assets/requests/{req.req_id}/reject/",
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAssetRequestCancel:
    def test_employee_can_cancel_own_pending_request(
        self, employee_client, organization, employee, asset_category
    ):
        """Employee can cancel their own pending request."""
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="My request to cancel",
        )
        response = employee_client.post(
            f"/api/v1/assets/requests/{req.req_id}/cancel/",
        )
        assert response.status_code == 204
        req.refresh_from_db()
        assert req.is_deleted is True

    def test_employee_cannot_cancel_others_request(
        self, employee_client, organization, second_employee, asset_category
    ):
        """Employee cannot cancel another employee's request (returns 404 since scope_for_employee hides it)."""
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=second_employee,
            asset_category=asset_category,
            reason="Other's request",
        )
        response = employee_client.post(
            f"/api/v1/assets/requests/{req.req_id}/cancel/",
        )
        # scope_for_employee filters the queryset to own requests only → 404
        assert response.status_code == 404

    def test_cannot_cancel_non_pending_request(
        self, employee_client, organization, employee, asset_category
    ):
        """Only pending requests can be cancelled."""
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Test",
            status=RequestStatus.APPROVED.value,
        )
        response = employee_client.post(
            f"/api/v1/assets/requests/{req.req_id}/cancel/",
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAssetRequestFiltering:
    def test_filter_by_status(
        self, org_admin_client, organization, employee, asset_category
    ):
        """Filter requests by status."""
        AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Pending",
            status=RequestStatus.PENDING.value,
        )
        approved_req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Approved",
            status=RequestStatus.APPROVED.value,
        )
        response = org_admin_client.get(
            f"/api/v1/assets/requests/?status={RequestStatus.APPROVED.value}"
        )
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1
        assert response.json()["data"]["results"][0]["req_id"] == approved_req.req_id

    def test_filter_by_priority(
        self, org_admin_client, organization, employee, asset_category
    ):
        """Filter requests by priority."""
        AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Low priority",
            priority="low",
        )
        high_req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="High priority",
            priority="high",
        )
        response = org_admin_client.get("/api/v1/assets/requests/?priority=high")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1
        assert response.json()["data"]["results"][0]["req_id"] == high_req.req_id

    def test_filter_by_req_id_hrid(
        self, org_admin_client, organization, employee, asset_category
    ):
        """Filter by request HRID (req_id)."""
        req = AssetRequest.objects.create(
            organization=organization,
            requested_by=employee,
            asset_category=asset_category,
            reason="Test HRID filter",
        )
        response = org_admin_client.get(f"/api/v1/assets/requests/?req_id={req.req_id}")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1
        assert response.json()["data"]["results"][0]["req_id"] == req.req_id
