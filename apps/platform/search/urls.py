"""
apps/platform/search/urls.py — Global search URL.
"""

from django.urls import path

from .views import GlobalSearchView

urlpatterns = [
    path("", GlobalSearchView.as_view(), name="global-search"),
]
