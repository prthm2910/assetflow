"""
apps/assets/requests/services.py — Business logic for AssetRequest workflow.

Keeps the AssetRequestViewSet thin: HTTP concerns stay in the view,
domain logic lives here (testable without HTTP clients).
"""

from apps.assets.categories.models import AssetCategory
from apps.assets.requests.constants import RequestStatus
from apps.assets.requests.models import AssetRequest


class AssetRequestService:
    """
    Domain operations for asset request workflow.

    Usage:
        request = AssetRequestService.submit(user, data)
    """

    @staticmethod
    def submit(user, validated_data):
        """
        Submit a new asset request on behalf of the user.

        Resolves the submitting organization from:
        - The user's organization (for org-scoped users)
        - The category's organization (for super admins without an org)

        Sets status to PENDING and links to the user's employee profile.

        Args:
            user: The requesting user.
            validated_data: Dict of validated request fields. `asset_category`
                is already a model instance from serializer validation.

        Returns:
            Tuple of (AssetRequest instance, error_response_or_None).
        """
        user_org = getattr(user, "organization", None)

        # Resolve organization for super admin path (no org on user)
        if user_org is None:
            category = validated_data.get("asset_category")
            if category:
                # Serializer already resolved this to a model instance
                if hasattr(category, "organization"):
                    submit_org = category.organization
                else:
                    return None, "Category not found."
            else:
                return None, "Category not found."
        else:
            submit_org = user_org

        # Resolve employee profile
        employee = user.employee
        if not employee:
            return None, "No employee profile found for the current user."

        # Create the request
        request_obj = AssetRequest.objects.create(
            organization=submit_org,
            requested_by=employee,
            asset_category=validated_data["asset_category"],
            reason=validated_data["reason"],
            priority=validated_data.get("priority", RequestStatus.PENDING.value),
            status=RequestStatus.PENDING.value,
            created_by=user,
        )

        return request_obj, None
