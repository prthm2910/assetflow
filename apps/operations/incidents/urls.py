"""apps/operations/incidents/urls.py — URL routing for Incidents."""

from rest_framework.routers import DefaultRouter

from apps.operations.incidents.views import IncidentViewSet


router = DefaultRouter()
router.register(r"", IncidentViewSet, basename="incidents")

urlpatterns = router.urls
