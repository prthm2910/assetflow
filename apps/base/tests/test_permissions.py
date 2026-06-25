"""
apps/base/tests/test_permissions.py — Tests for RoleBasedPermission.
"""

import pytest
from unittest.mock import Mock
from rest_framework.test import APIRequestFactory

from apps.base.permissions import RoleBasedPermission
from apps.base.constants import UserRole


def make_request(method="GET", user=None):
    """Create a mock API request with the given method and user."""
    factory = APIRequestFactory()
    method = method.upper()
    if method == "GET":
        request = factory.get("/")
    elif method == "POST":
        request = factory.post("/")
    elif method == "PUT":
        request = factory.put("/")
    elif method == "PATCH":
        request = factory.patch("/")
    elif method == "DELETE":
        request = factory.delete("/")
    else:
        request = factory.options("/")
    request.user = user
    return request


def make_user(role=None, is_authenticated=True):
    """Create a mock user with the specified role."""
    user = Mock()
    user.is_authenticated = is_authenticated
    user.role = role
    return user


class TestRoleBasedPermission:
    """Tests for RoleBasedPermission."""

    # --- Unauthenticated users ---

    def test_unauthenticated_denied_read(self):
        """Unauthenticated users should be denied on read."""
        request = make_request("GET")
        request.user = None
        permission = RoleBasedPermission()
        assert permission.has_permission(request, None) is False

    def test_unauthenticated_denied_write(self):
        """Unauthenticated users should be denied on write."""
        request = make_request("POST")
        request.user = None
        permission = RoleBasedPermission()
        assert permission.has_permission(request, None) is False

    # --- Super admin bypass ---

    def test_super_admin_read_unrestricted(self):
        """Super admin bypasses read restrictions."""
        user = make_user(role=UserRole.SUPER_ADMIN.value)
        request = make_request("GET", user)
        permission = RoleBasedPermission(
            read_roles=[UserRole.EMPLOYEE],
        )
        assert permission.has_permission(request, None) is True

    def test_super_admin_write_unrestricted(self):
        """Super admin bypasses write restrictions."""
        user = make_user(role=UserRole.SUPER_ADMIN.value)
        request = make_request("POST", user)
        permission = RoleBasedPermission(
            write_roles=[UserRole.EMPLOYEE],
        )
        assert permission.has_permission(request, None) is True

    # --- Read permission ---

    def test_read_allowed_when_no_restriction(self):
        """Read is allowed when read_roles is empty (no restriction)."""
        user = make_user(role=UserRole.EMPLOYEE.value)
        request = make_request("GET", user)
        permission = RoleBasedPermission()
        assert permission.has_permission(request, None) is True

    def test_read_denied_when_role_not_in_read_roles(self):
        """Read is denied when user's role is not in read_roles."""
        user = make_user(role=UserRole.EMPLOYEE.value)
        request = make_request("GET", user)
        permission = RoleBasedPermission(
            read_roles=[UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN],
        )
        assert permission.has_permission(request, None) is False

    def test_read_allowed_when_role_in_read_roles(self):
        """Read is allowed when user's role is in read_roles."""
        user = make_user(role=UserRole.ORG_ADMIN.value)
        request = make_request("GET", user)
        permission = RoleBasedPermission(
            read_roles=[UserRole.ORG_ADMIN, UserRole.EMPLOYEE],
        )
        assert permission.has_permission(request, None) is True

    # --- Write permission ---

    def test_write_allowed_when_no_restriction(self):
        """Write is allowed when write_roles is empty (no restriction)."""
        user = make_user(role=UserRole.EMPLOYEE.value)
        request = make_request("POST", user)
        permission = RoleBasedPermission()
        assert permission.has_permission(request, None) is True

    def test_write_denied_when_role_not_in_write_roles(self):
        """Write is denied when user's role is not in write_roles."""
        user = make_user(role=UserRole.EMPLOYEE.value)
        request = make_request("POST", user)
        permission = RoleBasedPermission(
            write_roles=[UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN],
        )
        assert permission.has_permission(request, None) is False

    def test_write_allowed_when_role_in_write_roles(self):
        """Write is allowed when user's role is in write_roles."""
        user = make_user(role=UserRole.ORG_ADMIN.value)
        request = make_request("POST", user)
        permission = RoleBasedPermission(
            write_roles=[UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN],
        )
        assert permission.has_permission(request, None) is True

    # --- HTTP method → read vs write mapping ---

    def test_put_is_write(self):
        """PUT should be treated as write operation."""
        user = make_user(role=UserRole.EMPLOYEE.value)
        request = make_request("PUT", user)
        permission = RoleBasedPermission(
            write_roles=[UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN],
        )
        assert permission.has_permission(request, None) is False

    def test_patch_is_write(self):
        """PATCH should be treated as write operation."""
        user = make_user(role=UserRole.EMPLOYEE.value)
        request = make_request("PATCH", user)
        permission = RoleBasedPermission(
            write_roles=[UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN],
        )
        assert permission.has_permission(request, None) is False

    def test_delete_is_write(self):
        """DELETE should be treated as write operation."""
        user = make_user(role=UserRole.EMPLOYEE.value)
        request = make_request("DELETE", user)
        permission = RoleBasedPermission(
            write_roles=[UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN],
        )
        assert permission.has_permission(request, None) is False

    def test_options_is_read(self):
        """OPTIONS should be treated as read operation."""
        user = make_user(role=UserRole.EMPLOYEE.value)
        request = make_request("OPTIONS", user)
        permission = RoleBasedPermission(
            read_roles=[UserRole.SUPER_ADMIN],
        )
        assert permission.has_permission(request, None) is False

    def test_head_is_read(self):
        """HEAD should be treated as read operation."""
        user = make_user(role=UserRole.EMPLOYEE.value)
        request = APIRequestFactory().head("/")
        request.user = user
        permission = RoleBasedPermission(
            read_roles=[UserRole.SUPER_ADMIN],
        )
        assert permission.has_permission(request, None) is False
