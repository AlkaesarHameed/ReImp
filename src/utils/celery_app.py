"""
Celery Application
Background task processing
Source: https://docs.celeryq.dev/en/stable/getting-started/first-steps-with-celery.html
Verified: 2025-11-14
"""

from celery import Celery

from src.api.config import settings

# Initialize Celery app
# Evidence: Celery for distributed task processing
# Source: https://docs.celeryq.dev/en/stable/userguide/configuration.html
# Verified: 2025-11-14
celery_app = Celery(
    "starter",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Auto-discover tasks
# Tasks should be in src/tasks/*.py
celery_app.autodiscover_tasks(["src.tasks"])
