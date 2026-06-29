"""
URL configuration for the AssetFlow project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


urlpatterns = [
    path("admin/", admin.site.urls),
    # API v1 — modules are included here as they are implemented
    path("api/v1/users/", include("apps.core.users.urls")),
    path("api/v1/organizations/", include("apps.core.organizations.urls")),
    path("api/v1/employees/", include("apps.core.employees.urls")),
    path("api/v1/assets/", include("apps.assets.urls")),
    path("api/v1/incidents/", include("apps.operations.incidents.urls")),
    path("api/v1/licenses/", include("apps.operations.licenses.urls")),
    path("api/v1/notifications/", include("apps.platform.notifications.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
