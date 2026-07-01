"""
config/django.py — Django app, middleware, templates, and auth configuration.
"""

# ==============================================================================
# Django Built-in Apps
# ==============================================================================
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

# ==============================================================================
# Local Apps (AssetFlow modules)
# ==============================================================================
LOCAL_APPS = [
    "apps.base",
    "apps.core.users",
    "apps.core.organizations",
    "apps.core.employees",
    "apps.assets.categories",
    "apps.assets.inventory",
    "apps.assets.allocations",
    "apps.assets.requests",
    "apps.operations.incidents",
    "apps.operations.licenses",
    "apps.platform.notifications",
    "apps.platform.audit",
    "apps.platform.search",
]

# ==============================================================================
# Middleware
# ==============================================================================
DJANGO_DEFAULT_MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

LOCAL_MIDDLEWARE = [
    "apps.base.middleware.RequestMiddleware",     # Thread-local user/IP for audit signals
    "apps.base.middleware.RequestIDMiddleware",   # X-Request-ID for request tracing
]

# ==============================================================================
# Templates
# ==============================================================================
DJANGO_CORE_TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

# ==============================================================================
# Password Validation
# ==============================================================================
DJANGO_AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
