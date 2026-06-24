"""
apps/core/users/tests/test_serializers.py — Tests for user serializers.
"""

import pytest


@pytest.mark.django_db
class TestUserSerializer:
    """Tests for UserSerializer."""

    def test_user_serializer_exists(self):
        """UserSerializer should exist."""
        from apps.core.users.serializers import UserSerializer

        assert UserSerializer is not None

    def test_user_serializer_has_expected_fields(self):
        """Serializer should have expected fields."""
        from apps.core.users.serializers import UserSerializer

        serializer = UserSerializer()
        expected_fields = {
            "user_id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
        }
        assert expected_fields.issubset(set(serializer.fields.keys()))


@pytest.mark.django_db
class TestUserCreateSerializer:
    """Tests for UserCreateSerializer."""

    def test_user_create_serializer_exists(self):
        """UserCreateSerializer should exist."""
        from apps.core.users.serializers import UserCreateSerializer

        assert UserCreateSerializer is not None

    def test_create_user_with_password(self):
        """Should create user with provided password."""
        from apps.core.users.serializers import UserCreateSerializer

        data = {
            "username": "newuser1",
            "email": "newuser1@example.com",
            "password": "TestPass123!",
            "first_name": "New",
            "last_name": "User",
        }
        serializer = UserCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()
        assert user.username == "newuser1"
        assert user.must_change_password is True
        # Response should include temp_password for admin to share
        assert "temp_password" in serializer.data

    def test_create_user_requires_password(self):
        """Creating user without password should fail validation."""
        from apps.core.users.serializers import UserCreateSerializer

        data = {
            "username": "newuser2",
            "email": "newuser2@example.com",
            "first_name": "Another",
            "last_name": "User",
        }
        serializer = UserCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "password" in serializer.errors


@pytest.mark.django_db
class TestLoginSerializer:
    """Tests for LoginSerializer."""

    def test_login_serializer_exists(self):
        """LoginSerializer should exist."""
        from apps.core.users.serializers import LoginSerializer

        assert LoginSerializer is not None

    def test_login_requires_email_and_password(self):
        """Login should require email and password."""
        from apps.core.users.serializers import LoginSerializer

        # Missing password
        serializer = LoginSerializer(data={"email": "test@example.com"})
        assert not serializer.is_valid()
        assert "password" in serializer.errors

    def test_login_valid_credentials(self, user):
        """Login should accept valid credentials."""
        from apps.core.users.serializers import LoginSerializer

        serializer = LoginSerializer(
            data={
                "email": user.email,
                "password": "testpass123",
            }
        )
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestChangePasswordSerializer:
    """Tests for ChangePasswordSerializer."""

    def test_change_password_serializer_exists(self):
        """ChangePasswordSerializer should exist."""
        from apps.core.users.serializers import ChangePasswordSerializer

        assert ChangePasswordSerializer is not None

    def test_change_password_has_required_fields(self):
        """Serializer should have old_password and new_password fields."""
        from apps.core.users.serializers import ChangePasswordSerializer

        serializer = ChangePasswordSerializer()
        assert "old_password" in serializer.fields
        assert "new_password" in serializer.fields


@pytest.mark.django_db
class TestPasswordResetRequestSerializer:
    """Tests for PasswordResetRequestSerializer."""

    def test_password_reset_request_serializer_exists(self):
        """PasswordResetRequestSerializer should exist."""
        from apps.core.users.serializers import PasswordResetRequestSerializer

        assert PasswordResetRequestSerializer is not None

    def test_requires_email(self):
        """Should require email field."""
        from apps.core.users.serializers import PasswordResetRequestSerializer

        serializer = PasswordResetRequestSerializer(data={})
        assert not serializer.is_valid()
        assert "email" in serializer.errors

    def test_valid_email_accepted(self):
        """Should accept valid email."""
        from apps.core.users.serializers import PasswordResetRequestSerializer

        serializer = PasswordResetRequestSerializer(data={"email": "test@example.com"})
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestPasswordResetConfirmSerializer:
    """Tests for PasswordResetConfirmSerializer."""

    def test_password_reset_confirm_serializer_exists(self):
        """PasswordResetConfirmSerializer should exist."""
        from apps.core.users.serializers import PasswordResetConfirmSerializer

        assert PasswordResetConfirmSerializer is not None

    def test_has_required_fields(self):
        """Serializer should have token and new_password fields."""
        from apps.core.users.serializers import PasswordResetConfirmSerializer

        serializer = PasswordResetConfirmSerializer()
        assert "token" in serializer.fields
        assert "new_password" in serializer.fields
