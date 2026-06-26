"""
apps/assets/allocations/urls.py — URL routing for Asset Allocations.
"""

from rest_framework.routers import DefaultRouter

from apps.assets.allocations.views import AllocationViewSet


router = DefaultRouter()
router.register(r"allocations", AllocationViewSet, basename="allocations")

urlpatterns = router.urls
