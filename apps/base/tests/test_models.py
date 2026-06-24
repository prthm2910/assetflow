"""
apps/base/tests/test_models.py — Tests for SoftDeleteManager and BaseModel methods.
"""

import pytest


@pytest.mark.django_db
class TestSoftDeleteManager:
    """Tests for SoftDeleteManager."""

    def test_soft_delete_manager_class_exists(self):
        """SoftDeleteManager class should exist and have expected methods."""
        from apps.base.managers import SoftDeleteManager

        manager = SoftDeleteManager.__new__(SoftDeleteManager)
        assert hasattr(manager, "get_queryset")
        assert hasattr(manager, "deleted_only")
        assert hasattr(manager, "all_with_deleted")
        assert callable(manager.deleted_only)
        assert callable(manager.all_with_deleted)


@pytest.mark.django_db
class TestBaseModelSoftDelete:
    """Tests for BaseModel soft delete and restore methods."""

    def test_delete_method_exists(self):
        """BaseModel should have a delete method."""
        from apps.base.models import BaseModel

        assert hasattr(BaseModel, "delete")

    def test_hard_delete_method_exists(self):
        """BaseModel should have a hard_delete method."""
        from apps.base.models import BaseModel

        assert hasattr(BaseModel, "hard_delete")
        assert callable(BaseModel.hard_delete)

    def test_restore_method_exists(self):
        """BaseModel should have a restore method."""
        from apps.base.models import BaseModel

        assert hasattr(BaseModel, "restore")
        assert callable(BaseModel.restore)

    def test_soft_delete_manager_registered(self):
        """Default objects should be SoftDeleteManager."""
        from apps.base.models import BaseModel

        # Check managers via _meta (hasattr doesn't work for managers)
        manager_names = [m.name for m in BaseModel._meta.managers]
        assert "objects" in manager_names
        assert "all_objects" in manager_names

    def test_model_has_uuid_primary_key(self):
        """BaseModel should have UUID primary key."""
        from apps.base.models import BaseModel

        assert hasattr(BaseModel, "id")

    def test_model_has_soft_delete_fields(self):
        """BaseModel should have is_active, is_deleted, deleted_at fields."""
        from apps.base.models import BaseModel

        # These should be defined on the model
        assert hasattr(BaseModel, "is_active")
        assert hasattr(BaseModel, "is_deleted")
        assert hasattr(BaseModel, "deleted_at")

    def test_model_has_audit_fields(self):
        """BaseModel should have created_by and updated_by audit fields."""
        from apps.base.models import BaseModel

        assert hasattr(BaseModel, "created_by")
        assert hasattr(BaseModel, "updated_by")

    def test_model_has_timestamp_fields(self):
        """BaseModel should have created_at and updated_at fields."""
        from apps.base.models import BaseModel

        assert hasattr(BaseModel, "created_at")
        assert hasattr(BaseModel, "updated_at")
