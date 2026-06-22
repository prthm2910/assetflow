"""
apps/base/tests/test_viewsets.py — Tests for BaseViewSet and BulkOperationsMixin.
"""
import pytest
from rest_framework.test import APIRequestFactory
from unittest.mock import Mock

from apps.base.viewsets import BaseViewSet, BulkOperationsMixin
from apps.base.enums import UserRole


# NOTE: `user` fixture is provided by conftest.py (project root).

@pytest.mark.django_db
class TestBaseViewSet:
    """Tests for BaseViewSet queryset scoping."""

    def test_super_admin_sees_all(self, user):
        """Super admin should see all data."""
        user.role = UserRole.SUPER_ADMIN.value
        user.is_superuser = True
        user.save()

        request = APIRequestFactory().get('/')
        request.user = user

        viewset = BaseViewSet()
        viewset.request = request
        viewset.action = 'list'
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

        request = APIRequestFactory().post('/')
        request.user = user

        viewset = BaseViewSet()
        viewset.request = request
        viewset.get_serializer_context = lambda: {'request': request}

        class MockSerializer:
            def save(self, **kwargs):
                assert kwargs.get('created_by') == user

        viewset.perform_create(MockSerializer())

    def test_perform_update_sets_updated_by(self, user):
        """perform_update should set updated_by."""
        user.role = UserRole.SUPER_ADMIN.value
        user.is_superuser = True
        user.save()

        request = APIRequestFactory().patch('/')
        request.user = user

        viewset = BaseViewSet()
        viewset.request = request

        class MockSerializer:
            def save(self, **kwargs):
                assert kwargs.get('updated_by') == user

        viewset.perform_update(MockSerializer())


@pytest.mark.django_db
class TestBulkOperationsMixin:
    """Tests for BulkOperationsMixin."""

    def test_bulk_create_is_action(self):
        """bulk_create should be a registered action."""
        assert hasattr(BulkOperationsMixin, 'bulk_create')

    def test_bulk_update_is_action(self):
        """bulk_update should be a registered action."""
        assert hasattr(BulkOperationsMixin, 'bulk_update')

    def test_bulk_delete_is_action(self):
        """bulk_delete should be a registered action."""
        assert hasattr(BulkOperationsMixin, 'bulk_delete')
