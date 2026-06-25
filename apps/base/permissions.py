"""
apps/base/permissions.py — Reusable DRF permission classes.

Permission classes for role-based and org-based access control.
"""

from rest_framework import permissions

from apps.base.constants import UserRole


class IsSuperAdmin(permissions.BasePermission):
    """
    Allows access only to super admins (platform-level administrators).
    """

    def has_permission(self, request, view):
        if not request.user:
            return False
        if not getattr(request.user, "is_authenticated", False):
            return False
        return getattr(request.user, "role", None) == UserRole.SUPER_ADMIN.value


class IsOrgAdmin(permissions.BasePermission):
    """
    Allows access only to organization administrators.
    """

    def has_permission(self, request, view):
        if not request.user:
            return False
        if not getattr(request.user, "is_authenticated", False):
            return False
        return getattr(request.user, "role", None) == UserRole.ORG_ADMIN.value


class IsOrgMember(permissions.BasePermission):
    """
    Allows access to any authenticated user belonging to an organization.
    Super admins can access everything.
    """

    def has_permission(self, request, view):
        if not request.user or not getattr(request.user, "is_authenticated", False):
            return False
        if getattr(request.user, "role", None) == UserRole.SUPER_ADMIN.value:
            return True
        return getattr(request.user, "organization", None) is not None


class IsObjectOwnerOrAdmin(permissions.BasePermission):
    """
    Allows access if user owns the object, is an org admin, or is a super admin.

    Checks common ownership fields: user, created_by, reported_by, requested_by.
    Subclasses can override _is_owner for custom ownership logic.
    """

    def has_permission(self, request, view):
        return request.user and getattr(request.user, "is_authenticated", False)

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Super admin always has access
        if getattr(user, "role", None) == UserRole.SUPER_ADMIN.value:
            return True

        # Org admin has access to their org's objects
        if getattr(user, "role", None) == UserRole.ORG_ADMIN.value:
            # Check if object belongs to user's org
            if hasattr(obj, "organization"):
                user_org = getattr(user, "organization", None)
                obj_org = getattr(obj, "organization", None)
                if user_org and obj_org and user_org.id == obj_org.id:
                    return True

        return self._is_owner(user, obj)

    def _is_owner(self, user, obj):
        """Check if user owns the object via common ownership fields."""
        if hasattr(obj, "user") and obj.user == user:
            return True
        if hasattr(obj, "created_by") and obj.created_by == user:
            return True
        if hasattr(obj, "reported_by"):
            employee = getattr(user, "employee_profile", None)
            if employee and obj.reported_by == employee:
                return True
        if hasattr(obj, "requested_by"):
            employee = getattr(user, "employee_profile", None)
            if employee and obj.requested_by == employee:
                return True
        return False


class IsSelfOrAdmin(permissions.BasePermission):
    """
    Allows access if user is the object itself or an admin.
    Used for profile/own-record endpoints.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Super admin always has access
        if getattr(user, "role", None) == UserRole.SUPER_ADMIN.value:
            return True

        # User accessing their own record
        if obj == user:
            return True
        if hasattr(obj, "user") and obj.user == user:
            return True
        if hasattr(obj, "email") and obj.email == user.email:
            return True

        # Org admin can access any object in their org
        if getattr(user, "role", None) == UserRole.ORG_ADMIN.value:
            if hasattr(obj, "organization"):
                user_org = getattr(user, "organization", None)
                obj_org = getattr(obj, "organization", None)
                if user_org and obj_org and user_org.id == obj_org.id:
                    return True

        return False


# ==============================================================================
# Role-Based Permission Class
# ==============================================================================


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

    def __init__(self, read_roles: list = None, write_roles: list = None):
        """
        Args:
            read_roles: List of UserRole enum members allowed to read. Defaults to [] (all authenticated).
            write_roles: List of UserRole enum members allowed to write. Defaults to [] (all authenticated).
        """
        self.read_roles = read_roles or []
        self.write_roles = write_roles or []

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
