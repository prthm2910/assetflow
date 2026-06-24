"""
apps/base/urls.py — URL routing for the base app.

This module is included in the main URL config at /api/v1/.
Routes are added here as modules are implemented.
"""

from django.urls import path


# Placeholder — routes will be added as modules are implemented
urlpatterns = [
    # health check endpoint
    path(
        "health/",
        lambda r: __import__("django.http", fromlist=["JsonResponse"]).JsonResponse(
            {"status": "ok"}
        ),
        name="health",
    ),
]
