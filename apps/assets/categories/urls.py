"""
apps/assets/categories/urls.py — URL routing for Asset Categories.
"""

from rest_framework.routers import DefaultRouter

from apps.assets.categories.views import AssetCategoryViewSet


router = DefaultRouter()
router.register(r"asset-categories", AssetCategoryViewSet, basename="assetcategory")

urlpatterns = router.urls
