"""apps/operations/incidents/tests/test_views.py — API tests for Incident endpoints."""

import pytest

from apps.operations.incidents.constants import IncidentStatus
from apps.operations.incidents.models import Incident


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_incident(client, organization, asset, employee, title="Test incident", description="Test desc"):
    """Create an incident via API and return the response."""
    return client.post(
        "/api/v1/incidents/",
        {
            "asset": str(asset.id),
            "title": title,
            "description": description,
        },
    )


def create_incident_report(client, asset, employee, title="Test incident", description="Test desc", **kwargs):
    """Create an incident via the /report/ action."""
    return client.post(
        "/api/v1/incidents/report/",
        {
            "asset": str(asset.id),
            "title": title,
            "description": description,
            **kwargs,
        },
    )


# ---------------------------------------------------------------------------
# List / Create (Report)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIncidentListCreate:
    def test_super_admin_can_list_all_orgs(
        self, super_admin_client, organization, second_organization,
        employee, asset, asset_category
    ):
        """Super admin sees incidents across all organizations."""
        from django.contrib.auth import get_user_model
        from apps.core.employees.models import Employee

        User = get_user_model()
        second_user = User.objects.create_user(
            username="second_incident_emp",
            email="second_incident@test.com",
            password="testpass123",
            first_name="Second",
            last_name="Incident",
            role="employee",
            organization_id=second_organization.id,
        )
        second_emp = Employee.objects.create(
            organization=second_organization,
            user=second_user,
            designation="Test",
        )
        Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Incident 1", description="desc 1",
            category="other",
        )
        Incident.objects.create(
            organization=second_organization, asset=asset,
            reported_by=second_emp, title="Incident 2", description="desc 2",
            category="other",
        )
        response = super_admin_client.get("/api/v1/incidents/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 2

    def test_org_admin_sees_own_org_only(
        self, org_admin_client, organization, second_organization,
        employee, asset, asset_category
    ):
        """Org admin sees only incidents in their organization."""
        from django.contrib.auth import get_user_model
        from apps.core.employees.models import Employee

        User = get_user_model()
        second_user = User.objects.create_user(
            username="second_incident_emp2",
            email="second_incident2@test.com",
            password="testpass123",
            first_name="Second",
            last_name="Incident",
            role="employee",
            organization_id=second_organization.id,
        )
        second_emp = Employee.objects.create(
            organization=second_organization,
            user=second_user,
            designation="Test",
        )
        Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Incident 1", description="desc 1",
            category="other",
        )
        Incident.objects.create(
            organization=second_organization, asset=asset,
            reported_by=second_emp, title="Incident 2", description="desc 2",
            category="other",
        )
        response = org_admin_client.get("/api/v1/incidents/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_employee_sees_only_own_incidents(
        self, employee_client, organization, employee, asset, second_employee
    ):
        """Employee sees only incidents they reported."""
        Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="My incident", description="desc 1",
            category="other",
        )
        Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=second_employee, title="Other incident", description="desc 2",
            category="other",
        )
        response = employee_client.get("/api/v1/incidents/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_unauthenticated_denied(self, api_client):
        response = api_client.get("/api/v1/incidents/")
        assert response.status_code == 401

    def test_org_admin_can_create(
        self, org_admin_client, organization, employee, asset, org_admin_employee
    ):
        """Org admin can report an incident."""
        response = create_incident_report(
            org_admin_client, asset, employee,
            title="Broken screen",
            description="Screen cracked after drop.",
            category="hardware",
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["asset"] == str(asset.id)
        assert data["status"] == IncidentStatus.REPORTED.value
        assert data["inc_id"].startswith("INC")

    def test_employee_can_report(
        self, employee_client, organization, employee, asset
    ):
        """Employee can report an incident."""
        response = create_incident_report(
            employee_client, asset, employee,
            title="Keyboard not working",
            description="Several keys are unresponsive.",
            category="performance",
        )
        assert response.status_code == 201

    def test_employee_cannot_set_status_on_create(
        self, employee_client, organization, employee, asset
    ):
        """Employee cannot override status when reporting."""
        response = employee_client.post(
            "/api/v1/incidents/report/",
            {
                "asset": str(asset.id),
                "title": "Test",
                "description": "Test desc",
                "status": "closed",
                "category": "hardware",
            },
        )
        assert response.status_code == 201
        assert response.json()["data"]["status"] == IncidentStatus.REPORTED.value

    def test_create_requires_employee_profile(self, super_admin_client, asset):
        """Super admin without employee profile gets 400."""
        response = super_admin_client.post(
            "/api/v1/incidents/report/",
            {
                "asset": str(asset.id),
                "title": "Test",
                "description": "Test desc",
            },
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Retrieve / Update / Delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIncidentRetrieveUpdateDelete:
    def test_can_retrieve_incident(self, org_admin_client, organization, employee, asset):
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
        )
        response = org_admin_client.get(f"/api/v1/incidents/{incident.inc_id}/")
        assert response.status_code == 200
        assert response.json()["data"]["inc_id"] == incident.inc_id

    def test_can_partial_update_incident(self, org_admin_client, organization, employee, asset):
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
        )
        response = org_admin_client.patch(
            f"/api/v1/incidents/{incident.inc_id}/",
            {"title": "Updated title"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["title"] == "Updated title"

    def test_can_delete_incident(self, org_admin_client, organization, employee, asset):
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
        )
        response = org_admin_client.delete(f"/api/v1/incidents/{incident.inc_id}/")
        assert response.status_code == 204
        incident.refresh_from_db()
        assert incident.is_deleted is True

    def test_employee_cannot_update(self, employee_client, organization, employee, asset):
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
        )
        response = employee_client.patch(
            f"/api/v1/incidents/{incident.inc_id}/",
            {"title": "Hacked"},
        )
        assert response.status_code == 403

    def test_employee_cannot_delete(self, employee_client, organization, employee, asset):
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
        )
        response = employee_client.delete(f"/api/v1/incidents/{incident.inc_id}/")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Assign
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIncidentAssign:
    def test_admin_can_assign_incident(
        self, org_admin_client, organization, employee, asset, second_employee
    ):
        """Org admin can assign an incident to an employee."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
        )
        response = org_admin_client.post(
            f"/api/v1/incidents/{incident.inc_id}/assign/",
            {"assigned_to": str(second_employee.id)},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["assigned_to"] == str(second_employee.id)

    def test_assign_transitions_reported_to_open(
        self, org_admin_client, organization, employee, asset, second_employee
    ):
        """Assigning a reported incident transitions it to open."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
            status=IncidentStatus.REPORTED.value,
        )
        response = org_admin_client.post(
            f"/api/v1/incidents/{incident.inc_id}/assign/",
            {"assigned_to": str(second_employee.id)},
        )
        assert response.status_code == 200
        incident.refresh_from_db()
        assert incident.status == IncidentStatus.OPEN.value

    def test_assign_does_not_change_non_reported_status(
        self, org_admin_client, organization, employee, asset, second_employee
    ):
        """Assigning an already-open incident does not change its status."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
            status=IncidentStatus.IN_PROGRESS.value,
        )
        response = org_admin_client.post(
            f"/api/v1/incidents/{incident.inc_id}/assign/",
            {"assigned_to": str(second_employee.id)},
        )
        assert response.status_code == 200
        incident.refresh_from_db()
        assert incident.status == IncidentStatus.IN_PROGRESS.value

    def test_employee_cannot_assign(self, employee_client, organization, employee, asset):
        """Employee cannot assign incidents."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
        )
        response = employee_client.post(
            f"/api/v1/incidents/{incident.inc_id}/assign/",
            {"assigned_to": str(employee.id)},
        )
        assert response.status_code == 403

    def test_cannot_assign_cross_org_employee(
        self, org_admin_client, organization, second_organization,
        employee, asset
    ):
        """Cannot assign an incident to an employee from a different org."""
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
            designation="Other Org Employee",
        )
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
        )
        response = org_admin_client.post(
            f"/api/v1/incidents/{incident.inc_id}/assign/",
            {"assigned_to": str(other_emp.id)},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Resolve
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIncidentResolve:
    def test_admin_can_resolve_in_progress_incident(
        self, org_admin_client, organization, employee, asset
    ):
        """Org admin can resolve an in_progress incident."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
            status=IncidentStatus.IN_PROGRESS.value,
        )
        response = org_admin_client.post(
            f"/api/v1/incidents/{incident.inc_id}/resolve/",
            {"resolution_notes": "Fixed the screen."},
        )
        assert response.status_code == 200
        incident.refresh_from_db()
        assert incident.status == IncidentStatus.RESOLVED.value
        assert incident.resolved_at is not None
        assert "Fixed the screen" in incident.resolution_notes

    def test_cannot_resolve_non_in_progress(
        self, org_admin_client, organization, employee, asset
    ):
        """Cannot resolve a reported incident (must be in_progress first)."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
        )
        response = org_admin_client.post(
            f"/api/v1/incidents/{incident.inc_id}/resolve/",
            {"resolution_notes": "Fixed."},
        )
        assert response.status_code == 400

    def test_cannot_resolve_already_resolved(
        self, org_admin_client, organization, employee, asset
    ):
        """Cannot resolve an already resolved incident."""
        from django.utils import timezone

        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
            status=IncidentStatus.RESOLVED.value,
            resolved_at=timezone.now(),
        )
        response = org_admin_client.post(
            f"/api/v1/incidents/{incident.inc_id}/resolve/",
        )
        assert response.status_code == 400

    def test_employee_cannot_resolve(self, employee_client, organization, employee, asset):
        """Employee cannot resolve incidents."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
            status=IncidentStatus.IN_PROGRESS.value,
        )
        response = employee_client.post(
            f"/api/v1/incidents/{incident.inc_id}/resolve/",
            {"resolution_notes": "Fixed."},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Close
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIncidentClose:
    def test_admin_can_close_resolved_incident(
        self, org_admin_client, organization, employee, asset
    ):
        """Org admin can close a resolved incident."""
        from django.utils import timezone

        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
            status=IncidentStatus.RESOLVED.value,
            resolved_at=timezone.now(),
        )
        response = org_admin_client.post(
            f"/api/v1/incidents/{incident.inc_id}/close/",
            {"close_notes": "Verified by manager."},
        )
        assert response.status_code == 200
        incident.refresh_from_db()
        assert incident.status == IncidentStatus.CLOSED.value
        assert incident.closed_at is not None

    def test_cannot_close_non_resolved(
        self, org_admin_client, organization, employee, asset
    ):
        """Cannot close an incident that is not resolved."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
        )
        response = org_admin_client.post(
            f"/api/v1/incidents/{incident.inc_id}/close/",
        )
        assert response.status_code == 400

    def test_employee_cannot_close(self, employee_client, organization, employee, asset):
        """Employee cannot close incidents."""
        from django.utils import timezone

        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
            status=IncidentStatus.RESOLVED.value,
            resolved_at=timezone.now(),
        )
        response = employee_client.post(
            f"/api/v1/incidents/{incident.inc_id}/close/",
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Add Attachment
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIncidentAttachments:
    def test_admin_can_add_attachment(
        self, org_admin_client, organization, employee, asset
    ):
        """Org admin can add an attachment URL."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
        )
        response = org_admin_client.post(
            f"/api/v1/incidents/{incident.inc_id}/attachments/",
            {"attachment_url": "https://example.com/photo.jpg"},
        )
        assert response.status_code == 200
        incident.refresh_from_db()
        assert "https://example.com/photo.jpg" in incident.attachments

    def test_can_add_multiple_attachments(
        self, org_admin_client, organization, employee, asset
    ):
        """Multiple attachments can be added."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
        )
        org_admin_client.post(
            f"/api/v1/incidents/{incident.inc_id}/attachments/",
            {"attachment_url": "https://example.com/1.jpg"},
        )
        org_admin_client.post(
            f"/api/v1/incidents/{incident.inc_id}/attachments/",
            {"attachment_url": "https://example.com/2.jpg"},
        )
        incident.refresh_from_db()
        assert len(incident.attachments) == 2

    def test_attachment_requires_url(
        self, org_admin_client, organization, employee, asset
    ):
        """attachment_url field is required."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
        )
        response = org_admin_client.post(
            f"/api/v1/incidents/{incident.inc_id}/attachments/",
            {},
        )
        assert response.status_code == 400

    def test_employee_cannot_add_attachment(self, employee_client, organization, employee, asset):
        """Employee cannot add attachments."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            category="other",
        )
        response = employee_client.post(
            f"/api/v1/incidents/{incident.inc_id}/attachments/",
            {"attachment_url": "https://example.com/photo.jpg"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIncidentFiltering:
    def test_filter_by_inc_id(
        self, org_admin_client, organization, employee, asset
    ):
        """Filter incidents by incident HRID."""
        i1 = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Incident 1", description="desc 1",
            category="other",
        )
        Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Incident 2", description="desc 2",
            category="other",
        )
        response = org_admin_client.get(
            f"/api/v1/incidents/?inc_id={i1.inc_id}"
        )
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_filter_by_status(
        self, org_admin_client, organization, employee, asset
    ):
        """Filter incidents by status."""
        Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Reported", description="desc",
            category="other",
            status=IncidentStatus.REPORTED.value,
        )
        Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Resolved", description="desc",
            category="other",
            status=IncidentStatus.RESOLVED.value,
        )
        response = org_admin_client.get("/api/v1/incidents/?status=resolved")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_filter_by_category(
        self, org_admin_client, organization, employee, asset
    ):
        """Filter incidents by category."""
        Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Hardware issue", description="desc",
            category="hardware",
        )
        Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Other issue", description="desc",
            category="other",
        )
        response = org_admin_client.get("/api/v1/incidents/?category=hardware")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1
