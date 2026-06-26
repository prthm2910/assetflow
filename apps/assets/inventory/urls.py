"""
apps/assets/inventory/urls.py — URL routing for Asset Inventory.
"""

from rest_framework.routers import DefaultRouter

from apps.assets.inventory.views import AssetViewSet


router = DefaultRouter()
router.register(r"inventory", AssetViewSet, basename="inventory-asset")

urlpatterns = router.urls
