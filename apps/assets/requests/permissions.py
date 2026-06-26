"""
apps/assets/requests/permissions.py — Custom permissions for AssetRequest workflow.

Org isolation is handled at the queryset level by BaseViewSet.scope_queryset().
These permission classes enforce role and relationship-based access only.
"""

from apps.base.constants import UserRole
from apps.base.permissions import RoleBasedPermission


class IsRequesterOrManagerOrAdmin(RoleBasedPermission):
    """
    Allows: requester, requester's direct manager, org admin, or super admin.

    Org isolation is already enforced by BaseViewSet.scope_queryset() which filters
    the queryset to the user's organization. This class adds manager-relationship
    checks on top of that foundation.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        role = getattr(user, "role", None)

        # Super admin: always allowed (scope_queryset already grants full access)
        if role == UserRole.SUPER_ADMIN.value:
            return True

        # Org admin: always allowed (scope_queryset already scoped to their org)
        if role == UserRole.ORG_ADMIN.value:
            return True

        employee = getattr(user, "employee_profile", None)

        # Requester themselves
        requested_by_id = getattr(obj, "requested_by_id", None)
        if employee and requested_by_id and requested_by_id == employee.id:
            return True

        # Requester's direct manager
        if employee and requested_by_id:
            try:
                requested_by = obj.requested_by
                if requested_by:
                    manager = getattr(requested_by, "manager", None)
                    if manager and manager.id == employee.id:
                        return True
            except Exception:
                pass

        return False


class IsManagerOrAdmin(RoleBasedPermission):
    """
    Allows: requester's direct manager, org admin, or super admin.

    Denies: the requester themselves (only their manager and admins can act).

    Org isolation is already enforced by BaseViewSet.scope_queryset().
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        role = getattr(user, "role", None)

        # Super admin: always allowed (scope_queryset already grants full access)
        if role == UserRole.SUPER_ADMIN.value:
            return True

        # Org admin: always allowed (scope_queryset already scoped to their org)
        if role == UserRole.ORG_ADMIN.value:
            return True

        # Employee: must be the requester's direct manager
        employee = getattr(user, "employee_profile", None)
        if employee:
            try:
                requested_by = getattr(obj, "requested_by", None)
                if requested_by:
                    manager = getattr(requested_by, "manager", None)
                    if manager and manager.id == employee.id:
                        return True
            except Exception:
                pass

        return False
