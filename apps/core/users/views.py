"""
apps/core/users/views.py — Views for authentication and user management.
"""

from datetime import timedelta

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
import logging

from apps.base.constants import UserRole
from apps.base.response import error_response, success_response
from apps.base.viewsets import BaseViewSet
from apps.core.users.models import PasswordResetToken
from apps.core.users.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    TokenRefreshSerializer,
    UserCreateSerializer,
    UserListSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

logger = logging.getLogger(__name__)


User = get_user_model()


@extend_schema_view(
    register=extend_schema(
        tags=["Authentication"],
        summary="Register",
        description="Public self-registration for new users. Returns JWT tokens for immediate login.",
        request=UserRegistrationSerializer,
        responses={201: None},
    ),
    login=extend_schema(
        tags=["Authentication"],
        summary="Login",
        description="Authenticate user with email and password. Returns JWT access and refresh tokens.",
        request=LoginSerializer,
        responses={200: None},
    ),
    refresh=extend_schema(
        tags=["Authentication"],
        summary="Refresh access token",
        description="Exchange a valid refresh token for a new access token.",
        request={
            "application/json": {
                "type": "object",
                "required": ["refresh"],
                "properties": {
                    "refresh": {
                        "type": "string",
                        "description": "Valid refresh token from login",
                    }
                },
            }
        },
        responses={200: None},
    ),
    logout=extend_schema(
        tags=["Authentication"],
        summary="Logout",
        description="Logout and blacklist refresh token. Pass refresh token in request body.",
        request={
            "application/json": {
                "type": "object",
                "required": ["refresh"],
                "properties": {
                    "refresh": {
                        "type": "string",
                        "description": "Refresh token to blacklist",
                    }
                },
            }
        },
        responses={200: None},
    ),
    me=extend_schema(
        tags=["Profile"],
        summary="Get/Update current user",
        description="Get current user profile (GET) or update own profile (PATCH). Requires authentication.",
        responses={200: None},
    ),
    change_password=extend_schema(
        tags=["Profile"],
        summary="Change password",
        description="Change current user password. Requires old password, new password, and confirmation.",
        request=ChangePasswordSerializer,
        responses={200: None},
    ),
    password_reset=extend_schema(
        tags=["Authentication"],
        summary="Request password reset",
        description="Request password reset email. Returns success even if email does not exist (prevents enumeration).",
        request=PasswordResetRequestSerializer,
        responses={200: None},
    ),
    password_reset_confirm=extend_schema(
        tags=["Authentication"],
        summary="Confirm password reset",
        description="Confirm password reset with token received via email.",
        request=PasswordResetConfirmSerializer,
        responses={200: None},
    ),
)
class AuthViewSet(viewsets.GenericViewSet):
    """
    Authentication endpoints: register, login, logout, me, password change/reset.
    """

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @action(
        detail=False,
        methods=["post"],
        url_path="register",
        permission_classes=[AllowAny],
    )
    def register(self, request):
        """Public self-registration endpoint."""
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens for immediate login
        refresh = RefreshToken.for_user(user) # type: ignore
        logger.info("User registered: %s", user.email)

        return success_response(
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            message="Registration successful.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        """Authenticate user and return JWT tokens."""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"] # type: ignore
        refresh = RefreshToken.for_user(user)

        response_data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

        if user.must_change_password:
            logger.info("Login with password-change-required: %s", user.email)
            return success_response(
                data=response_data,
                message="Login successful. Please change your password.",
            )

        logger.info("User logged in: %s", user.email)
        return success_response(data=response_data, message="Login successful.")

    @action(detail=False, methods=["post"], url_path="refresh", permission_classes=[AllowAny])
    def refresh(self, request):
        """Exchange a valid refresh token for a new access token."""
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh: "RefreshToken" = serializer.validated_data["refresh"]  # type: ignore
        logger.debug("Token refreshed for user via refresh token")
        return success_response(
            data={
                "access": str(refresh.access_token),
            },
            message="Token refreshed successfully.",
        )

    @action(detail=False, methods=["post"], url_path="logout", permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        Logout and blacklist refresh token.

        Requires authenticated user. Pass refresh token in request body.
        """
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            logger.info("User logged out: %s", request.user.email)
            return success_response(message="Logged out successfully.")
        except Exception:
            logger.info("User logged out (token cleanup skipped): %s", request.user.email)
            return success_response(message="Logged out successfully.")

    @action(detail=False, methods=["get", "patch"], url_path="me", permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get or update current user profile."""
        if not request.user.is_authenticated:
            return error_response(
                message="Authentication required.",
                code="AUTHENTICATION_REQUIRED",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if request.method == "GET":
            return success_response(data=UserSerializer(request.user).data)

        # PATCH - update profile
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=UserSerializer(request.user).data)

    @action(detail=False, methods=["post"], url_path="change-password", permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """Change password (authenticated users only)."""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info("Password changed for user: %s", request.user.email)
        return success_response(message="Password changed successfully.")

    @action(detail=False, methods=["post"], url_path="password-reset")
    def password_reset(self, request):
        """Request password reset email."""
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower() # type: ignore

        try:
            user = User.objects.get(email__iexact=email)

            # Create reset token

            token = get_random_string(64)
            expires_at = timezone.now() + timedelta(hours=24)

            PasswordResetToken.objects.create(
                user=user,
                token=token,
                expires_at=expires_at,
            )
            logger.info("Password reset token created for: %s", email)

            # TODO: Send email with reset link
            # send_mail(
            #     subject='Password Reset',
            #     message=f'Click here to reset: https://app.example.com/reset/{token}/',
            #     from_email=settings.DEFAULT_FROM_EMAIL,
            #     recipient_list=[user.email],
            # )

        except User.DoesNotExist:
            logger.debug("Password reset requested for non-existent email: %s", email)
            pass  # Don't reveal if user exists

        # Always return success to prevent email enumeration
        return success_response(
            message="If an account with that email exists, a password reset email has been sent."
        )

    @action(detail=False, methods=["post"], url_path="password-reset-confirm")
    def password_reset_confirm(self, request):
        """Confirm password reset with token."""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info("Password reset confirmed successfully")
        return success_response(message="Password has been reset successfully.")


@extend_schema_view(
    list=extend_schema(
        tags=["User Management"],
        summary="List users",
        description="List all users. Super admin sees all, org admin sees organization users.",
    ),
    retrieve=extend_schema(
        tags=["User Management"],
        summary="Get user details",
        description="Get details of a specific user by user_id.",
    ),
    create=extend_schema(
        tags=["User Management"],
        summary="Create user",
        description="Create a new user. Only super admins can create users.",
    ),
    update=extend_schema(
        tags=["User Management"],
        summary="Update user",
        description="Update user details. Only super admins can update users.",
    ),
    partial_update=extend_schema(
        tags=["User Management"],
        summary="Partial update user",
        description="Partially update user details. Only super admins can update users.",
    ),
    destroy=extend_schema(
        tags=["User Management"],
        summary="Delete user",
        description="Soft delete a user. Only super admins can delete users.",
    ),
)
class UserViewSet(BaseViewSet):
    """
    User management: CRUD, toggle active, reset password.

    Permissions:
        - Read (GET): Super admin and org admin only
        - Write (POST/PUT/PATCH/DELETE): Super admin only
    """

    serializer_class = UserSerializer
    lookup_field = "user_id"
    ordering_fields = ["date_joined", "email", "first_name"]
    ordering = ["-date_joined"]

    # Read: super admin + org admin | Write: super admin only
    read_roles = [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]
    write_roles = [UserRole.SUPER_ADMIN]

    def get_queryset(self):
        user: User = self.request.user   # type: ignore

        # Super admin sees all users
        if user.role == UserRole.SUPER_ADMIN.value:
            return User.objects.all().order_by("-date_joined")

        # Org admin sees users in their organization
        if user.role == UserRole.ORG_ADMIN.value:
            if not user.organization:
                return User.objects.none()
            return User.objects.filter(
                organization=user.organization
            ).order_by("-date_joined")

        # Employees see only themselves
        return User.objects.filter(id=user.id)

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        if self.action == "list":
            return UserListSerializer
        return UserSerializer

    @extend_schema(
        tags=["User Management"],
        summary="Toggle user active status",
        description="Activate or deactivate a user. Cannot deactivate own account.",
    )
    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, user_id=None):
        """Toggle user active status."""
        user = self.get_object()

        # Prevent self-deactivation
        if user.id == request.user.id:
            logger.warning("User %s attempted to deactivate own account", request.user.email)
            return error_response(message="Cannot deactivate your own account.")

        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])

        status_msg = "activated" if user.is_active else "deactivated"
        logger.info("User %s %s by %s", user.email, status_msg, request.user.email)
        return success_response(
            data=UserSerializer(user).data,
            message=f"User {'activated' if user.is_active else 'deactivated'} successfully.",
        )

    @extend_schema(
        tags=["User Management"],
        summary="Reset user password",
        description="Generate a new temporary password for a user. User will be forced to change it on next login.",
    )
    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, user_id=None):
        """Reset user password to new temp password."""
        user = self.get_object()

        temp_password = get_random_string(12) + "!1Aa"
        user.set_password(temp_password)
        user.must_change_password = True
        user.save(update_fields=["password", "must_change_password"])

        logger.info("Password reset for user %s by %s", user.email, request.user.email)
        return success_response(
            data={
                "id": str(user.id),
                "email": user.email,
                "temp_password": temp_password,
            },
            message="Password reset successfully. Share the temporary password with the user.",
        )
