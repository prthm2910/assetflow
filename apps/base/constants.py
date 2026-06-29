"""
apps/base/constants.py — System-wide constants and enumeration types.

All enums inherit from BaseEnum which provides a .choices() classmethod
that returns Django-compatible (value, label) tuples for use in model field
choices and serializer choices.
"""

from enum import Enum


class BaseEnum(Enum):
    """
    Base Enum for all system-wide choices. Auto-generates Django (value, label) tuples.

    Usage:
        class UserRole(BaseEnum):
            ADMIN = 'admin'
            EMPLOYEE = 'employee'

        # Returns [('admin', 'Admin'), ('employee', 'Employee')]
        UserRole.choices()
    """

    @classmethod
    def choices(cls):
        """Return Django-compatible (value, label) tuples for all members."""
        return [
            (member.value, member.value.replace("_", " ").title())
            for member in cls
            if not member.name.startswith("_")
        ]

    @classmethod
    def values(cls):
        """Return a list of all member values."""
        return [member.value for member in cls if not member.name.startswith("_")]


# ==============================================================================
# User Roles
#
# Kept in base — used by base/permissions.py (RoleBasedPermission),
# base/viewsets.py (scope_queryset), and every app's permission checks.
# Moving to core/users would create a circular dependency:
#   base → users (import UserRole) → base (import BaseModel).
# ==============================================================================
class UserRole(BaseEnum):
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    EMPLOYEE = "employee"
