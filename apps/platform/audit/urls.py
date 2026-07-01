"""
apps/platform/audit/urls.py — URL routing for AuditLog ViewSet.
"""

from rest_framework.routers import DefaultRouter

from apps.platform.audit.views import AuditLogViewSet

router = DefaultRouter()
router.register("", AuditLogViewSet, basename="audit-logs")

urlpatterns = router.urls
