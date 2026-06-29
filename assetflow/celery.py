"""
celery.py — Celery application configuration for AssetFlow.

This module initializes the Celery app and configures the beat schedule.
Beat tasks are registered here and imported from their respective apps.
"""

import os

from celery import Celery
from celery.schedules import crontab


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "assetflow.settings")

app = Celery("assetflow")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Beat schedule — tasks are added by their respective modules.
# Module 10 (licenses) adds check_license_expiry and check_warranty_expiry.
app.conf.beat_schedule = {
    "check-license-expiry": {
        "task": "apps.platform.notifications.tasks.check_license_expiry",
        "schedule": crontab(hour=0, minute=0),  # Daily at midnight
    },
    "check-warranty-expiry": {
        "task": "apps.platform.notifications.tasks.check_warranty_expiry",
        "schedule": crontab(hour=0, minute=5),  # Daily at 00:05
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
