"""
config/third_party.py — Third-party app configuration.
"""

# ==============================================================================
# Third-Party Apps
# ==============================================================================
THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    "phonenumber_field",
]

# ==============================================================================
# DRF Spectacular (OpenAPI/Swagger) Settings
# ==============================================================================
SPECTACULAR_SETTINGS = {
    "TITLE": "AssetFlow API",
    "DESCRIPTION": "Multi-Tenant Asset Management System",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}
