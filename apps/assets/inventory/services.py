"""apps/assets/inventory/services.py — Business logic for Asset operations.

Keeps the AssetViewSet thin: HTTP concerns stay in the view,
domain logic lives here (testable without HTTP clients).
"""

import logging

from django.utils import timezone

from apps.base.constants import UserRole
from apps.assets.inventory.models import Asset

logger = logging.getLogger(__name__)


class AssetService:
    """
    Domain operations for Asset lifecycle.

    Usage:
        AssetService.inject_organization(user, data)  # mutates data in place
        serializer = AssetSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        asset = serializer.save()

        asset = AssetService.change_status(asset, "maintenance", user)
    """

    @staticmethod
    def inject_organization(user, data):
        """
        Inject the correct organization into request data based on user role.

        Non-super-admins can only create assets for their own organization.
        Super admins can specify any organization; if omitted, uses their own.

        Mutates `data` in place.

        Args:
            user: The requesting user.
            data: Dict of raw request data (will be mutated).
        """
        user_org = getattr(user, "organization", None)

        if not getattr(user, "is_super_admin", False):
            if user_org:
                data["organization"] = str(user_org.id)
        elif user_org and "organization" not in data:
            data["organization"] = str(user_org.id)

    @staticmethod
    def resolve_organization(user, related_model=None, related_id=None):
        """
        Resolve the correct organization for a write operation.

        Priority:
        1. User's own org (for org-scoped users)
        2. Related object's org (for super admins without an org)
        3. None (super admin with no org and no related object)

        Args:
            user: The requesting user.
            related_model: Django model class to resolve from (e.g. Asset).
            related_id: PK of the related object.

        Returns:
            Organization instance or None.
        """
        user_org = getattr(user, "organization", None)
        if user_org:
            return user_org

        # Super admin without org — resolve from related object
        if related_model and related_id:
            try:
                obj = related_model.objects.select_related("organization").get(
                    pk=related_id
                )
                return obj.organization
            except related_model.DoesNotExist:
                pass

        return None

    @staticmethod
    def change_status(asset, new_status, user):
        """
        Transition an asset's lifecycle status with audit fields.

        Args:
            asset: The Asset instance to update.
            new_status: Target status value (validated by caller).
            user: The user performing the change.

        Returns:
            The updated Asset instance.
        """
        old_status = asset.status
        asset.status = new_status
        asset.updated_by = user
        asset.save(update_fields=["status", "updated_at", "updated_by"])
        logger.info(
            "Asset %s status: %s → %s by %s",
            asset.asset_id,
            old_status,
            new_status,
            user.email,
        )
        return asset
