"""
Django settings for the AssetFlow project.
Assembles configuration from modular config/ files.
"""

import logging
import os
from pathlib import Path

import environ

from config.django import (
    DJANGO_APPS,
    DJANGO_AUTH_PASSWORD_VALIDATORS,
    DJANGO_CORE_TEMPLATES,
    DJANGO_DEFAULT_MIDDLEWARE,
    LOCAL_APPS,
    LOCAL_MIDDLEWARE,
)
from config.drf import REST_FRAMEWORK
from config.logging import LOGGING
from config.third_party import SPECTACULAR_SETTINGS, THIRD_PARTY_APPS
from config.utils import get_db_config, get_simple_jwt_config


logger = logging.getLogger(__name__)
logger.info("Starting AssetFlow settings initialization")

# ==============================================================================
# 1. Core Configuration
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env_file_path = BASE_DIR / ".env"
environ.Env.read_env(env_file_path)

# ==============================================================================
# 2. Security Settings
# ==============================================================================
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = bool(env("DJANGO_DEBUG"))
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# ==============================================================================
# 3. Installed Apps
# ==============================================================================
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ==============================================================================
# 4. Middleware
# ==============================================================================
MIDDLEWARE = DJANGO_DEFAULT_MIDDLEWARE + LOCAL_MIDDLEWARE

# ==============================================================================
# 5. URL Configuration
# ==============================================================================
ROOT_URLCONF = "assetflow.urls"
TEMPLATES = DJANGO_CORE_TEMPLATES
WSGI_APPLICATION = "assetflow.wsgi.application"

# ==============================================================================
# 6. Database
# ==============================================================================
DATABASES = get_db_config(env)
AUTH_USER_MODEL = env("AUTH_USER_MODEL")

# ==============================================================================
# 7. Password Validation
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = DJANGO_AUTH_PASSWORD_VALIDATORS

# ==============================================================================
# 8. Internationalization
# ==============================================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ==============================================================================
# 9. Static & Media Files
# ==============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# ==============================================================================
# 10. API Configuration (DRF & JWT)
# ==============================================================================
REST_FRAMEWORK = REST_FRAMEWORK
SIMPLE_JWT = get_simple_jwt_config(env)
SPECTACULAR_SETTINGS = SPECTACULAR_SETTINGS

# ==============================================================================
# 11. CORS Configuration
# ==============================================================================
CORS_ALLOW_ALL_ORIGINS = DEBUG
if not DEBUG:
    CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

# ==============================================================================
# 12. Default Auto Field
# ==============================================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==============================================================================
# 13. Logging Configuration
# ==============================================================================
LOGGING = LOGGING

# ==============================================================================
# 14. Cache Configuration (Redis)
# ==============================================================================
REDIS_URL = env("REDIS_URL")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# ==============================================================================
# 15. Email Configuration
# ==============================================================================
EMAIL_BACKEND = env("EMAIL_BACKEND")
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")

# ==============================================================================
# 16. Celery Configuration
# ==============================================================================
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# ==============================================================================
# 17. Security Headers
# ==============================================================================
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_SSL_REDIRECT = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# ==============================================================================
# 18. CORS
# ==============================================================================
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=False)
if CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = []
else:
    CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

logger.info("AssetFlow settings initialization completed")
