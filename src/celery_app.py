from __future__ import annotations

import os

try:
    from celery import Celery
except Exception:  # pragma: no cover - optional in test env
    Celery = None


def make_celery(app_name: str = "esports_trainer"):
    """Create a Celery app using `CELERY_BROKER_URL` or `REDIS_URL`.

    This function is import-safe: if Celery isn't installed it returns None.
    """
    broker = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL")
    if broker is None or Celery is None:
        return None
    celery = Celery(app_name, broker=broker)
    # simple config
    celery.conf.beat_schedule = {}
    celery.conf.timezone = os.getenv("TZ", "UTC")
    return celery
