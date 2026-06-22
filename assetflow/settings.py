"""
Django settings for the AssetFlow project.
Assembles configuration from modular config/ files.
"""
import os
from pathlib import Path
import environ
import logging

from config.django import (
    DJANGO_APPS,
    DJANGO_DEFAULT_MIDDLEWARE,
    DJANGO_CORE_TEMPLATES,
    DJANGO_AUTH_PASSWORD_VALIDATORS,
    LOCAL_MIDDLEWARE,
    LOCAL_APPS,
)
from config.drf import REST_FRAMEWORK
from config.third_party import THIRD_PARTY_APPS, SPECTACULAR_SETTINGS
from config.utils import get_db_config, get_simple_jwt_config
from config.logging import LOGGING

logger = logging.getLogger(__name__)
logger.info("Starting AssetFlow settings initialization")

# ==============================================================================
# 1. Core Configuration
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)
env_file_path = BASE_DIR / '.env'
environ.Env.read_env(env_file_path)

# ==============================================================================
# 2. Security Settings
# ==============================================================================
SECRET_KEY = env('DJANGO_SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

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
ROOT_URLCONF = 'assetflow.urls'
TEMPLATES = DJANGO_CORE_TEMPLATES
WSGI_APPLICATION = 'assetflow.wsgi.application'

# ==============================================================================
# 6. Database
# ==============================================================================
DATABASES = get_db_config(env)
AUTH_USER_MODEL = env('AUTH_USER_MODEL')

# ==============================================================================
# 7. Password Validation
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = DJANGO_AUTH_PASSWORD_VALIDATORS

# ==============================================================================
# 8. Internationalization
# ==============================================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# 9. Static & Media Files
# ==============================================================================
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

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
    CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS')

# ==============================================================================
# 12. Default Auto Field
# ==============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# 13. Logging Configuration
# ==============================================================================
LOGGING = LOGGING

logger.info("AssetFlow settings initialization completed")
