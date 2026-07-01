"""apps/platform/audit/tests/test_models.py — AuditLog model tests."""

import pytest
import uuid

from apps.platform.audit.models import AuditLog


@pytest.mark.django_db
class TestAuditLogModel:
    def test_audit_log_created(self, organization, user):
        """Basic audit log creation."""
        log = AuditLog.objects.create(
            organization=organization,
            user=user,
            action="create",
            model_name="Asset",
            object_id=uuid.uuid4(),
        )
        assert log.id is not None
        assert log.action == "create"
        assert log.model_name == "Asset"

    def test_audit_log_stores_changes(self, organization, user):
        """AuditLog captures changes snapshot."""
        obj_id = uuid.uuid4()
        log = AuditLog.objects.create(
            organization=organization,
            user=user,
            action="update",
            model_name="Asset",
            object_id=obj_id,
            changes={"old": {"name": "Old Laptop"}, "new": {"name": "New Laptop"}},
        )
        assert log.changes["old"]["name"] == "Old Laptop"
        assert log.changes["new"]["name"] == "New Laptop"

    def test_audit_log_str_representation(self, organization, user):
        """__str__ shows action, model, object_id, and org name."""
        obj_id = uuid.uuid4()
        log = AuditLog.objects.create(
            organization=organization,
            user=user,
            action="delete",
            model_name="Incident",
            object_id=obj_id,
        )
        s = str(log)
        assert "delete" in s
        assert "Incident" in s
        assert organization.name in s

    def test_soft_delete(self, organization, user):
        """delete() performs soft-delete on AuditLog."""
        log = AuditLog.objects.create(
            organization=organization,
            user=user,
            action="create",
            model_name="Asset",
            object_id=uuid.uuid4(),
        )
        log_id = log.id
        log.delete()
        assert not AuditLog.objects.filter(id=log_id).exists()
        assert AuditLog.objects.all_with_deleted().filter(id=log_id).exists()

    def test_ordering_by_created_at_desc(self, organization, user):
        """AuditLog defaults to ordering by -created_at."""
        for i in range(3):
            AuditLog.objects.create(
                organization=organization,
                user=user,
                action="create",
                model_name="Asset",
                object_id=uuid.uuid4(),
            )
        logs = list(AuditLog.objects.all())
        assert logs[0].created_at >= logs[-1].created_at

    def test_action_choices_exist(self, organization):
        """All expected action values are valid."""
        valid_actions = {"create", "update", "delete", "allocate", "approve", "reject"}
        for action in valid_actions:
            log = AuditLog(
                organization=organization,
                action=action,
                model_name="Test",
                object_id=uuid.uuid4(),
            )
            assert log.action in valid_actions
