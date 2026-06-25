"""
apps/base/permissions.py — Reusable DRF permission classes.

Permission classes for role-based and org-based access control.
"""

from rest_framework import permissions

from apps.base.constants import UserRole


class RoleBasedPermission(permissions.BasePermission):
    """
    Enterprise-grade role-based permission for ViewSets.

    Composable: set read_roles and/or write_roles to restrict access.
    Super admin bypasses all restrictions.

    Usage in ViewSet:
        class AssetViewSet(BaseViewSet):
            def get_permissions(self):
                if self.action in ["create", "update", "partial_update", "destroy"]:
                    return [RoleBasedPermission(write_roles=[UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN])]
                return []  # Read is unrestricted (default IsAuthenticated applies)

    Args:
        read_roles: List of roles allowed to READ. Empty = all authenticated.
        write_roles: List of roles allowed to WRITE. Empty = all authenticated.

    Examples:
        # Read-only for employees, write for admins
        RoleBasedPermission(
            read_roles=[UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN, UserRole.EMPLOYEE],
            write_roles=[UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]
        )

        # Write-only restriction (read is unrestricted)
        RoleBasedPermission(write_roles=[UserRole.SUPER_ADMIN])

        # Full restriction (no one can write without explicit role)
        RoleBasedPermission(
            read_roles=[UserRole.SUPER_ADMIN],
            write_roles=[UserRole.SUPER_ADMIN]
        )
    """

    def __init__(
        self,
        read_roles: list | None = None,
        write_roles: list | None = None,
    ):
        """
        Args:
            read_roles: List of UserRole enum members allowed to read. Defaults to [] (all authenticated).
            write_roles: List of UserRole enum members allowed to write. Defaults to [] (all authenticated).
        """
        self.read_roles: list = read_roles or []
        self.write_roles: list = write_roles or []

    def has_permission(self, request, view):
        """Check if user has permission based on role and HTTP method."""
        user = request.user

        # Authentication check
        if not user or not getattr(user, "is_authenticated", False):
            return False

        user_role = getattr(user, "role", None)

        # Super admin always has full access
        if user_role == UserRole.SUPER_ADMIN.value:
            return True

        # Write operation check (POST, PUT, PATCH, DELETE)
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            return self._check_write_permission(user_role)

        # Read operation check (GET, HEAD, OPTIONS)
        return self._check_read_permission(user_role)

    def _check_read_permission(self, user_role) -> bool:
        """Check if role is allowed to read. Empty read_roles = all authenticated."""
        if not self.read_roles:
            return True  # No restrictions on reads
        return user_role in [role.value for role in self.read_roles]

    def _check_write_permission(self, user_role) -> bool:
        """Check if role is allowed to write. Empty write_roles = all authenticated."""
        if not self.write_roles:
            return True  # No restrictions on writes
        return user_role in [role.value for role in self.write_roles]
