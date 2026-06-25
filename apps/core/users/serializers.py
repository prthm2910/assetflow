"""
apps/core/users/serializers.py — Serializers for User authentication and management.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.crypto import get_random_string
from rest_framework import serializers

from apps.base.constants import UserRole
from apps.base.serializers import BaseSerializer


User = get_user_model()


class UserSerializer(BaseSerializer):
    """Full user serializer with all fields."""

    class Meta:
        model = User
        fields = [
            "user_id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "organization",
            "role",
            "is_active",
            "is_staff",
            "must_change_password",
            "date_joined",
            "last_login",
            "is_superuser",
        ]
        read_only_fields = ["user_id", "date_joined", "last_login", "is_superuser"]


class UserCreateSerializer(BaseSerializer):
    """Serializer for creating new users with optional password."""

    password = serializers.CharField(write_only=True, required=False)
    temp_password = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "user_id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "organization",
            "must_change_password",
            "password",
            "temp_password",
            "date_joined",
        ]
        read_only_fields = ["user_id", "temp_password", "date_joined"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
            user.must_change_password = True  # type: ignore[attr-defined]
        else:
            # Auto-generate temp password only if none provided
            temp_password_str = get_random_string(length=12) + "!1Aa"
            user.set_password(temp_password_str)
            user.must_change_password = True  # type: ignore[attr-defined]
            user._temp_password = temp_password_str  # type: ignore[attr-defined]
        user.save()
        return user

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if hasattr(instance, "_temp_password"):
            data["temp_password"] = instance._temp_password  # type: ignore[attr-defined]
        return data


class UserUpdateSerializer(BaseSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone",
            "role",
            "organization",
            "is_active",
        ]

    def update(self, instance, validated_data):
        request_user = self.context["request"].user
        # Employees can only update their own profile
        if request_user.role == UserRole.EMPLOYEE.value:
            validated_data.pop("role", None)
            validated_data.pop("organization", None)
            validated_data.pop("is_active", None)
        return super().update(instance, validated_data)


class UserListSerializer(BaseSerializer):
    """Lightweight user serializer for list views."""

    class Meta:
        model = User
        fields = [
            "user_id",
            "email",
            "first_name",
            "last_name",
            "role",
            "organization",
            "is_active",
        ]


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        email = attrs.get("email", "").lower()
        password = attrs.get("password", "")

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")

        attrs["user"] = user
        return attrs


class TokenRefreshSerializer(serializers.Serializer):
    """Serializer for refreshing access tokens."""

    refresh = serializers.CharField(
        help_text="Valid refresh token issued during login."
    )

    def validate(self, attrs: dict) -> dict:
        from rest_framework_simplejwt.exceptions import TokenError
        from rest_framework_simplejwt.tokens import RefreshToken

        try:
            refresh = RefreshToken(attrs["refresh"])
            attrs["refresh"] = refresh
        except TokenError:
            raise serializers.ValidationError("Invalid or expired refresh token.")
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password with confirmation."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        user = self.context["request"].user

        # Verify old password
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError(
                {"old_password": "Current password is incorrect."}
            )

        # Verify password match
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "New password and confirmation do not match."}
            )

        # Validate password complexity (Django validators)
        validate_password(attrs["new_password"], user=user)

        return attrs

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.must_change_password = False  # type: ignore[attr-defined]
        user.save(update_fields=["password", "must_change_password"])
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting password reset."""

    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            User.objects.get(email__iexact=value)
        except User.DoesNotExist:
            pass  # Don't reveal if email exists
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset with token."""

    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate_token(self, value):
        from apps.core.users.models import PasswordResetToken

        try:
            token = PasswordResetToken.objects.get(token=value)
            if not token.is_valid:
                raise serializers.ValidationError(
                    "This reset token has expired or been used."
                )
            self._reset_token = token
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("Invalid reset token.")
        return value

    def validate_new_password(self, value):
        if hasattr(self, "_reset_token"):
            validate_password(value, user=self._reset_token.user)
        return value

    def save(self):
        token = self._reset_token
        user = token.user
        user.set_password(self.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        token.used = True
        token.save(update_fields=["used"])
        return user


class UserRegistrationSerializer(BaseSerializer):
    """Serializer for public user self-registration."""

    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "first_name", "last_name", "phone"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return value

    def validate_password(self, value):
        """Validate password complexity using Django validators."""
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = True  # Self-registered users are active
        user.save()
        return user
