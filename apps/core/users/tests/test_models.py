"""
apps/core/users/tests/test_models.py — Tests for User model and PasswordResetToken.
"""

import pytest
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
class TestUserModel:
    """Tests for User model."""

    def test_user_model_exists(self):
        """User model should exist."""
        from apps.core.users.models import User

        assert User is not None

    def test_user_has_hrid_field(self):
        """User should have user_id field for HRID."""
        from apps.core.users.models import User

        assert hasattr(User, "user_id")

    def test_user_has_role_field(self):
        """User should have role field."""
        from apps.core.users.models import User

        assert hasattr(User, "role")

    def test_user_has_organization_id(self):
        """User should have organization_id for multi-tenancy."""
        from apps.core.users.models import User

        assert hasattr(User, "organization_id")

    def test_user_has_must_change_password(self):
        """User should have must_change_password field."""
        from apps.core.users.models import User

        assert hasattr(User, "must_change_password")

    def test_user_has_phone_field(self):
        """User should have phone field with PhoneNumberField."""
        from apps.core.users.models import User

        assert hasattr(User, "phone")

    def test_user_hrid_auto_generated_on_save(self):
        """User ID (HRID) should be auto-generated on first save."""
        from apps.core.users.models import User

        user = User.objects.create_user(
            username="testuser1",
            email="test1@example.com",
            password="testpass123",
        )
        assert user.user_id is not None
        assert user.user_id.startswith("USR")

    def test_user_str_returns_email(self):
        """User __str__ should return email."""
        from apps.core.users.models import User

        user = User(username="testuser2", email="test2@example.com")
        assert str(user) == "test2@example.com"

    def test_user_default_role_is_employee(self):
        """New users should have default role of employee."""
        from apps.core.users.models import User
        from apps.base.constants import UserRole

        user = User(username="testuser3", email="test3@example.com")
        assert user.role == UserRole.EMPLOYEE.value

    def test_user_default_must_change_password_true(self):
        """New users should have must_change_password=True."""
        from apps.core.users.models import User

        user = User(username="testuser4", email="test4@example.com")
        assert user.must_change_password is True


@pytest.mark.django_db
class TestPasswordResetToken:
    """Tests for PasswordResetToken model."""

    def test_password_reset_token_model_exists(self):
        """PasswordResetToken model should exist."""
        from apps.core.users.models import PasswordResetToken

        assert PasswordResetToken is not None

    def test_token_has_user_foreign_key(self):
        """Token should have user FK."""
        from apps.core.users.models import PasswordResetToken

        assert hasattr(PasswordResetToken, "user")

    def test_token_has_token_field(self):
        """Token should have token CharField."""
        from apps.core.users.models import PasswordResetToken

        assert hasattr(PasswordResetToken, "token")

    def test_token_has_expires_at(self):
        """Token should have expires_at datetime field."""
        from apps.core.users.models import PasswordResetToken

        assert hasattr(PasswordResetToken, "expires_at")

    def test_token_has_used_flag(self):
        """Token should have used boolean field."""
        from apps.core.users.models import PasswordResetToken

        assert hasattr(PasswordResetToken, "used")

    def test_token_is_valid_property(self):
        """Token should have is_valid property."""
        from apps.core.users.models import PasswordResetToken

        assert hasattr(PasswordResetToken, "is_valid")

    def test_token_is_valid_when_not_used_and_not_expired(self):
        """Token is_valid should be True when not used and not expired."""
        from apps.core.users.models import User, PasswordResetToken

        user = User.objects.create_user(
            username="tokenuser1",
            email="token1@example.com",
            password="testpass123",
        )
        token = PasswordResetToken.objects.create(
            user=user,
            token="valid_token_123",
            expires_at=timezone.now() + timedelta(hours=1),
        )
        assert token.is_valid is True

    def test_token_is_invalid_when_used(self):
        """Token is_valid should be False when used."""
        from apps.core.users.models import User, PasswordResetToken

        user = User.objects.create_user(
            username="tokenuser2",
            email="token2@example.com",
            password="testpass123",
        )
        token = PasswordResetToken.objects.create(
            user=user,
            token="used_token_456",
            expires_at=timezone.now() + timedelta(hours=1),
            used=True,
        )
        assert token.is_valid is False

    def test_token_is_invalid_when_expired(self):
        """Token is_valid should be False when expired."""
        from apps.core.users.models import User, PasswordResetToken

        user = User.objects.create_user(
            username="tokenuser3",
            email="token3@example.com",
            password="testpass123",
        )
        token = PasswordResetToken.objects.create(
            user=user,
            token="expired_token_789",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        assert token.is_valid is False
