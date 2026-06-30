"""apps/platform/audit/tests/test_views.py — AuditLog ViewSet tests."""

import pytest
import uuid

from apps.platform.audit.models import AuditLog


@pytest.mark.django_db
class TestAuditLogViewSet:
    def test_list_returns_audit_logs(self, organization, org_admin_user, org_admin_client):
        """Org admin can list their org's audit logs."""
        AuditLog.objects.create(
            organization=organization,
            user=org_admin_user,
            action="create",
            model_name="Asset",
            object_id=uuid.uuid4(),
        )
        resp = org_admin_client.get("/api/v1/audit-logs/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["count"] >= 1

    def test_retrieve_single_log(self, organization, org_admin_user, org_admin_client):
        """Org admin can retrieve a single audit log by ID."""
        log = AuditLog.objects.create(
            organization=organization,
            user=org_admin_user,
            action="update",
            model_name="Asset",
            object_id=uuid.uuid4(),
            old_data={"name": "Old"},
            new_data={"name": "New"},
        )
        resp = org_admin_client.get(f"/api/v1/audit-logs/{log.id}/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["action"] == "update"
        assert data["data"]["old_data"]["name"] == "Old"
        assert data["data"]["new_data"]["name"] == "New"

    def test_org_isolation(self, organization, second_organization, org_admin_user, org_admin_client):
        """Org admin cannot see another org's audit logs."""
        AuditLog.objects.create(
            organization=second_organization,
            user=org_admin_user,
            action="create",
            model_name="Asset",
            object_id=uuid.uuid4(),
        )
        resp = org_admin_client.get("/api/v1/audit-logs/")
        assert resp.status_code == 200
        data = resp.json()
        # Only logs from the org_admin's own org should appear
        for log_data in data["data"]["results"]:
            assert log_data["organization"] != second_organization.id

    def test_employee_cannot_view_audit_logs(self, organization, employee, employee_client):
        """Employees have no access to audit logs."""
        AuditLog.objects.create(
            organization=organization,
            user=employee.user,
            action="create",
            model_name="Asset",
            object_id=uuid.uuid4(),
        )
        resp = employee_client.get("/api/v1/audit-logs/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["count"] == 0

    def test_filter_by_model_name(self, organization, org_admin_user, org_admin_client):
        """Filtering by model_name works."""
        AuditLog.objects.create(
            organization=organization,
            user=org_admin_user,
            action="create",
            model_name="Asset",
            object_id=uuid.uuid4(),
        )
        AuditLog.objects.create(
            organization=organization,
            user=org_admin_user,
            action="create",
            model_name="Incident",
            object_id=uuid.uuid4(),
        )
        resp = org_admin_client.get("/api/v1/audit-logs/?model_name=Asset")
        assert resp.status_code == 200
        data = resp.json()
        for log_data in data["data"]["results"]:
            assert log_data["model_name"] == "Asset"

    def test_filter_by_action(self, organization, org_admin_user, org_admin_client):
        """Filtering by action works."""
        AuditLog.objects.create(
            organization=organization,
            user=org_admin_user,
            action="create",
            model_name="Asset",
            object_id=uuid.uuid4(),
        )
        AuditLog.objects.create(
            organization=organization,
            user=org_admin_user,
            action="delete",
            model_name="Asset",
            object_id=uuid.uuid4(),
        )
        resp = org_admin_client.get("/api/v1/audit-logs/?action=delete")
        assert resp.status_code == 200
        data = resp.json()
        for log_data in data["data"]["results"]:
            assert log_data["action"] == "delete"

    def test_list_serializer_excludes_data_blobs(self, organization, org_admin_user, org_admin_client):
        """List serializer does not include old_data/new_data."""
        AuditLog.objects.create(
            organization=organization,
            user=org_admin_user,
            action="update",
            model_name="Asset",
            object_id=uuid.uuid4(),
            old_data={"secret": "value"},
            new_data={"secret": "new_value"},
        )
        resp = org_admin_client.get("/api/v1/audit-logs/")
        assert resp.status_code == 200
        data = resp.json()
        for log_data in data["data"]["results"]:
            assert "old_data" not in log_data
            assert "new_data" not in log_data

    def test_unauthenticated_access_denied(self, client):
        """Unauthenticated users cannot access audit logs."""
        resp = client.get("/api/v1/audit-logs/")
        assert resp.status_code in [401, 403]
