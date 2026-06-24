"""
apps/core/organizations/urls.py — URL routing for organizations.

Included at /api/v1/organizations/ from assetflow/urls.py.

Endpoints:
    GET|POST   /                     — list, create
    GET        /{org_id}/           — retrieve
    PUT|PATCH  /{org_id}/           — update, partial_update
    DELETE     /{org_id}/           — destroy
    POST       /{org_id}/toggle-active/
    GET|PATCH  /{org_id}/config/
    GET|PATCH  /profile/            — own org profile
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.core.organizations.views import (
    OrganizationProfileViewSet,
    OrganizationViewSet,
)


router = DefaultRouter()
router.register("", OrganizationViewSet, basename="organizations")

urlpatterns = [
    path(
        "profile/",
        OrganizationProfileViewSet.as_view({"get": "retrieve", "patch": "partial_update"}),
        name="org-profile",
    ),
] + router.urls
