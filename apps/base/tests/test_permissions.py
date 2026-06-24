"""
apps/base/tests/test_permissions.py — Tests for permission classes.

These tests mock the `role` attribute since auth.User doesn't have it.
The actual role field is added in Module 2 (custom User model).
"""

import pytest
from unittest.mock import Mock
from rest_framework.test import APIRequestFactory

from apps.base.permissions import (
    IsSuperAdmin,
    IsOrgAdmin,
    IsOrgMember,
    IsObjectOwnerOrAdmin,
    IsSelfOrAdmin,
)
from apps.base.enums import UserRole


def make_user(role=None, is_superuser=False):
    """Create a mock user with the specified role attribute."""
    user = Mock()
    user.is_authenticated = True
    user.role = role
    user.is_superuser = is_superuser
    return user


@pytest.mark.django_db
class TestIsSuperAdmin:
    """Tests for IsSuperAdmin permission."""

    def test_super_admin_has_access(self):
        """Super admin should have access."""
        user = make_user(role=UserRole.SUPER_ADMIN.value, is_superuser=True)
        request = APIRequestFactory().get("/")
        request.user = user
        permission = IsSuperAdmin()

        assert permission.has_permission(request, None) is True

    def test_org_admin_denied(self):
        """Org admin should be denied."""
        user = make_user(role=UserRole.ORG_ADMIN.value)
        request = APIRequestFactory().get("/")
        request.user = user
        permission = IsSuperAdmin()

        assert permission.has_permission(request, None) is False

    def test_employee_denied(self):
        """Employee should be denied."""
        user = make_user(role=UserRole.EMPLOYEE.value)
        request = APIRequestFactory().get("/")
        request.user = user
        permission = IsSuperAdmin()

        assert permission.has_permission(request, None) is False

    def test_unauthenticated_denied(self):
        """Unauthenticated users should be denied."""
        request = APIRequestFactory().get("/")
        request.user = None
        permission = IsSuperAdmin()

        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestIsOrgAdmin:
    """Tests for IsOrgAdmin permission."""

    def test_org_admin_has_access(self):
        """Org admin should have access."""
        user = make_user(role=UserRole.ORG_ADMIN.value)
        request = APIRequestFactory().get("/")
        request.user = user
        permission = IsOrgAdmin()

        assert permission.has_permission(request, None) is True

    def test_employee_denied(self):
        """Employee should be denied."""
        user = make_user(role=UserRole.EMPLOYEE.value)
        request = APIRequestFactory().get("/")
        request.user = user
        permission = IsOrgAdmin()

        assert permission.has_permission(request, None) is False

    def test_super_admin_denied(self):
        """Super admin should be denied (org-level check)."""
        user = make_user(role=UserRole.SUPER_ADMIN.value, is_superuser=True)
        request = APIRequestFactory().get("/")
        request.user = user
        permission = IsOrgAdmin()

        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestIsOrgMember:
    """Tests for IsOrgMember permission."""

    def test_super_admin_always_allowed(self):
        """Super admin always has access regardless of org."""
        user = make_user(role=UserRole.SUPER_ADMIN.value, is_superuser=True)
        request = APIRequestFactory().get("/")
        request.user = user
        permission = IsOrgMember()

        assert permission.has_permission(request, None) is True

    def test_org_admin_allowed(self):
        """Org admin should be allowed."""
        user = make_user(role=UserRole.ORG_ADMIN.value)
        request = APIRequestFactory().get("/")
        request.user = user
        permission = IsOrgMember()

        assert permission.has_permission(request, None) is True

    def test_employee_allowed(self):
        """Employee should be allowed."""
        user = make_user(role=UserRole.EMPLOYEE.value)
        request = APIRequestFactory().get("/")
        request.user = user
        permission = IsOrgMember()

        assert permission.has_permission(request, None) is True

    def test_unauthenticated_denied(self):
        """Unauthenticated users should be denied."""
        request = APIRequestFactory().get("/")
        request.user = None
        permission = IsOrgMember()

        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestIsObjectOwnerOrAdmin:
    """Tests for IsObjectOwnerOrAdmin permission."""

    def test_super_admin_has_object_permission(self):
        """Super admin should have object permission."""
        user = make_user(role=UserRole.SUPER_ADMIN.value, is_superuser=True)
        request = APIRequestFactory().get("/")
        request.user = user
        permission = IsObjectOwnerOrAdmin()

        class MockObj:
            pass

        obj = MockObj()
        assert permission.has_object_permission(request, None, obj) is True

    def test_owner_has_object_permission(self):
        """Object owner should have permission."""
        owner = make_user(role=UserRole.EMPLOYEE.value)
        request = APIRequestFactory().get("/")
        request.user = owner
        permission = IsObjectOwnerOrAdmin()

        class MockObj:
            user = owner

        obj = MockObj()
        assert permission.has_object_permission(request, None, obj) is True

    def test_non_owner_denied(self):
        """Non-owner should be denied."""
        owner = make_user(role=UserRole.EMPLOYEE.value)
        non_owner = make_user(role=UserRole.EMPLOYEE.value)
        request = APIRequestFactory().get("/")
        request.user = non_owner
        permission = IsObjectOwnerOrAdmin()

        class MockObj:
            user = owner

        obj = MockObj()
        assert permission.has_object_permission(request, None, obj) is False


@pytest.mark.django_db
class TestIsSelfOrAdmin:
    """Tests for IsSelfOrAdmin permission."""

    def test_super_admin_has_permission(self):
        """Super admin should have permission for any object."""
        user = make_user(role=UserRole.SUPER_ADMIN.value, is_superuser=True)
        request = APIRequestFactory().get("/")
        request.user = user
        permission = IsSelfOrAdmin()

        class MockObj:
            pass

        obj = MockObj()
        assert permission.has_object_permission(request, None, obj) is True
