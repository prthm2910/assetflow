"""
apps/assets/requests/urls.py — URL routing for Asset Requests.
"""

from rest_framework.routers import DefaultRouter

from apps.assets.requests.views import AssetRequestViewSet


router = DefaultRouter()
router.register(r"requests", AssetRequestViewSet, basename="requests")

urlpatterns = router.urls
