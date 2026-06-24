"""
apps/core/users/tests/test_views.py — Tests for AuthViewSet and UserViewSet endpoints.
"""

import pytest


@pytest.mark.django_db
class TestAuthViewSet:
    """Tests for authentication endpoints."""

    def test_register_success(self, api_client):
        """POST /api/v1/users/auth/register/ should create user and return tokens."""
        response = api_client.post(
            "/api/v1/users/auth/register/",
            {
                "username": "newuser_reg2",
                "email": "newuser_reg2@example.com",
                "password": "TestPass123!",
                "first_name": "New",
                "last_name": "User",
            },
        )
        assert response.status_code == 201
        assert "data" in response.data
        assert "access" in response.data["data"]
        assert "refresh" in response.data["data"]

    def test_register_duplicate_email(self, api_client, user):
        """Registration with existing email should fail."""
        response = api_client.post(
            "/api/v1/users/auth/register/",
            {
                "username": "different_user",
                "email": user.email,
                "password": "TestPass123!",
            },
        )
        assert response.status_code == 400
        assert "error" in response.data
        assert "email" in response.data.get("error", {}).get("details", {})

    def test_login_success(self, api_client, user):
        """POST /api/v1/users/auth/login/ should return only tokens."""
        response = api_client.post(
            "/api/v1/users/auth/login/",
            {
                "email": user.email,
                "password": "testpass123",
            },
        )
        assert response.status_code == 200
        assert "data" in response.data
        assert "access" in response.data["data"]
        assert "refresh" in response.data["data"]
        assert "user" not in response.data["data"]  # No user data in login response

    def test_login_invalid_credentials(self, api_client, user):
        """Login with wrong password should fail."""
        response = api_client.post(
            "/api/v1/users/auth/login/",
            {
                "email": user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 400

    def test_login_missing_fields(self, api_client):
        """Login without credentials should fail."""
        response = api_client.post("/api/v1/users/auth/login/", {})
        assert response.status_code == 400

    def test_me_authenticated(self, employee_client):
        """GET /api/v1/users/auth/me/ should return current user."""
        response = employee_client.get("/api/v1/users/auth/me/")
        assert response.status_code == 200
        assert "data" in response.data
        assert "email" in response.data["data"]

    def test_me_unauthenticated(self, api_client):
        """GET /api/v1/users/auth/me/ without auth should fail."""
        response = api_client.get("/api/v1/users/auth/me/")
        assert response.status_code == 401

    def test_update_me(self, employee_client, user):
        """PATCH /api/v1/users/auth/me/ should update current user."""
        response = employee_client.patch(
            "/api/v1/users/auth/me/",
            {
                "first_name": "Updated",
                "last_name": "Name",
            },
        )
        assert response.status_code == 200
        assert response.data["data"]["first_name"] == "Updated"
        assert response.data["data"]["last_name"] == "Name"

    def test_change_password_success(self, employee_client, user):
        """POST /api/v1/users/auth/change-password/ should change password."""
        response = employee_client.post(
            "/api/v1/users/auth/change-password/",
            {
                "old_password": "testpass123",
                "new_password": "NewPass123!",
                "confirm_password": "NewPass123!",
            },
        )
        assert response.status_code == 200
        # Verify new password works
        user.refresh_from_db()
        assert user.check_password("NewPass123!")

    def test_change_password_wrong_old(self, employee_client):
        """Change password with wrong old password should fail."""
        response = employee_client.post(
            "/api/v1/users/auth/change-password/",
            {
                "old_password": "wrongoldpass",
                "new_password": "NewPass123!",
                "confirm_password": "NewPass123!",
            },
        )
        assert response.status_code == 400

    def test_change_password_mismatch(self, employee_client):
        """Change password with mismatched confirm should fail."""
        response = employee_client.post(
            "/api/v1/users/auth/change-password/",
            {
                "old_password": "testpass123",
                "new_password": "NewPass123!",
                "confirm_password": "DifferentPass123!",
            },
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestUserViewSet:
    """Tests for User CRUD endpoints."""

    def test_list_users_as_admin(self, super_admin_client):
        """GET /api/v1/users/profiles/ should list users for admin."""
        response = super_admin_client.get("/api/v1/users/profiles/")
        assert response.status_code == 200

    def test_list_users_as_employee_forbidden(self, employee_client):
        """GET /api/v1/users/profiles/ should be forbidden for employee."""
        response = employee_client.get("/api/v1/users/profiles/")
        # Employee should get 403 - check_permissions should deny
        assert response.status_code == 403

    def test_create_user_as_admin(self, super_admin_client):
        """POST /api/v1/users/profiles/ should create user for admin."""
        response = super_admin_client.post(
            "/api/v1/users/profiles/",
            {
                "username": "newuser_test",
                "email": "newuser_test@example.com",
                "password": "TestPass123!",
                "first_name": "New",
                "last_name": "User",
            },
        )
        assert response.status_code == 201
        # Response wraps in data
        assert "data" in response.data
        assert "user_id" in response.data["data"]

    def test_retrieve_user_as_admin(self, super_admin_client, user):
        """GET /api/v1/users/profiles/{user_id}/ should retrieve user for admin."""
        response = super_admin_client.get(f"/api/v1/users/profiles/{user.user_id}/")
        assert response.status_code == 200

    def test_update_user_as_admin(self, super_admin_client, user):
        """PATCH /api/v1/users/profiles/{user_id}/ should update user for admin."""
        response = super_admin_client.patch(
            f"/api/v1/users/profiles/{user.user_id}/", {"first_name": "Updated"}
        )
        assert response.status_code == 200
        assert response.data["data"]["first_name"] == "Updated"

    def test_delete_user_as_admin(self, super_admin_client, user):
        """DELETE /api/v1/users/profiles/{user_id}/ should soft-delete user."""
        response = super_admin_client.delete(f"/api/v1/users/profiles/{user.user_id}/")
        assert response.status_code == 204

    def test_toggle_active_as_admin(self, super_admin_client, user):
        """POST /api/v1/users/profiles/{user_id}/toggle-active/ should toggle user."""
        # Deactivate
        response = super_admin_client.post(
            f"/api/v1/users/profiles/{user.user_id}/toggle-active/"
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_active is False

        # Reactivate
        response = super_admin_client.post(
            f"/api/v1/users/profiles/{user.user_id}/toggle-active/"
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_active is True

    def test_reset_password_as_admin(self, super_admin_client, user):
        """POST /api/v1/users/profiles/{user_id}/reset-password/ should reset password."""
        response = super_admin_client.post(
            f"/api/v1/users/profiles/{user.user_id}/reset-password/"
        )
        assert response.status_code == 200
        assert "temp_password" in response.data["data"]
