"""
apps/core/users/urls.py — URL routing for authentication and user management.

Endpoints (under /api/v1/users/):
    /auth/login/
    /auth/logout/
    /auth/me/
    /auth/change-password/
    /auth/password-reset/
    /auth/password-reset-confirm/
    /profiles/
    /profiles/{id}/
    /profiles/{id}/toggle-active/
    /profiles/{id}/reset-password/
"""

from rest_framework.routers import DefaultRouter

from apps.core.users.views import AuthViewSet, UserViewSet


router = DefaultRouter()
router.register("auth", AuthViewSet, basename="auth")
router.register("profiles", UserViewSet, basename="profiles")

urlpatterns = router.urls
