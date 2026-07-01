"""
apps/base/tests/test_viewsets.py — Tests for BaseViewSet.
"""

import pytest
from rest_framework.test import APIRequestFactory
from unittest.mock import Mock

from apps.base.viewsets import BaseViewSet
from apps.base.constants import UserRole


# NOTE: `user` fixture is provided by conftest.py (project root).


@pytest.mark.django_db
class TestBaseViewSet:
    """Tests for BaseViewSet queryset scoping."""

    def test_super_admin_sees_all(self, user):
        """Super admin should see all data."""
        user.role = UserRole.SUPER_ADMIN.value
        user.is_superuser = True
        user.save()

        request = APIRequestFactory().get("/")
        request.user = user

        viewset = BaseViewSet()
        viewset.request = request
        viewset.action = "list"
        viewset.kwargs = {}
        viewset.format_kwarg = None

        queryset = Mock()
        scoped = viewset.scope_queryset(queryset)

        # Super admin: queryset returned unchanged
        assert scoped == queryset

    def test_perform_create_sets_created_by(self, user):
        """perform_create should set created_by."""
        user.role = UserRole.SUPER_ADMIN.value
        user.is_superuser = True
        user.save()

        request = APIRequestFactory().post("/")
        request.user = user

        viewset = BaseViewSet()
        viewset.request = request
        viewset.get_serializer_context = lambda: {"request": request}

        class MockModel:
            created_by = None

        class MockSerializer:
            Meta = type("Meta", (), {"model": MockModel})()

            def save(self, **kwargs):
                assert kwargs.get("created_by") == user

        viewset.perform_create(MockSerializer())

    def test_perform_update_sets_updated_by(self, user):
        """perform_update should set updated_by."""
        user.role = UserRole.SUPER_ADMIN.value
        user.is_superuser = True
        user.save()

        request = APIRequestFactory().patch("/")
        request.user = user

        viewset = BaseViewSet()
        viewset.request = request

        class MockModel:
            pk = 1
            updated_by = None

        class MockSerializer:
            Meta = type("Meta", (), {"model": MockModel})()
            instance = MockModel()

            def save(self, **kwargs):
                assert kwargs.get("updated_by") == user

        viewset.perform_update(MockSerializer())
