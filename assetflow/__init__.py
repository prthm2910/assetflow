# assetflow/__init__.py
# Import Celery app so that shared_task works.
from .celery import app as celery_app

__all__ = ('celery_app',)
