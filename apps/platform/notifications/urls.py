"""apps/platform/notifications/urls.py — URL routing for Notifications."""

from rest_framework.routers import DefaultRouter

from apps.platform.notifications.views import NotificationViewSet


router = DefaultRouter()
router.register(r"", NotificationViewSet, basename="notifications")

urlpatterns = router.urls
