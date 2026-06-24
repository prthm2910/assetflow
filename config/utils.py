"""
config/utils.py — Factory functions for database and JWT configuration.

"""

import logging
from datetime import timedelta


logger = logging.getLogger(__name__)


def get_db_config(env) -> dict:
    """Build PostgreSQL database config from environment variables."""
    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME"),
            "USER": env("DB_USER"),
            "PASSWORD": env("DB_PASSWORD"),
            "HOST": env("DB_HOST"),
            "PORT": env("DB_PORT"),
        }
    }


def get_simple_jwt_config(env) -> dict:
    """Build Simple JWT config from environment variables."""
    access_token_hours = env.int("ACCESS_TOKEN_LIFETIME_HOURS")
    refresh_token_days = env.int("REFRESH_TOKEN_LIFETIME_DAYS")
    logger.debug(
        f"JWT config | Access: {access_token_hours}h | Refresh: {refresh_token_days}d"
    )
    return {
        "ACCESS_TOKEN_LIFETIME": timedelta(hours=access_token_hours),
        "REFRESH_TOKEN_LIFETIME": timedelta(days=refresh_token_days),
        "ROTATE_REFRESH_TOKENS": True,
        "BLACKLIST_AFTER_ROTATION": True,
        "AUTH_HEADER_TYPES": ("Bearer",),
    }
