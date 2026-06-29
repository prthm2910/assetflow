"""apps/operations/licenses/urls.py — URL routing for Licenses."""

from rest_framework.routers import DefaultRouter

from apps.operations.licenses.views import SoftwareLicenseViewSet


router = DefaultRouter()
router.register(r"", SoftwareLicenseViewSet, basename="licenses")

urlpatterns = router.urls
