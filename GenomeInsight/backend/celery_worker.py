"""Celery worker entry point.

Usage (worker):
    celery -A celery_worker.celery worker --loglevel=info

Usage (beat scheduler):
    celery -A celery_worker.celery beat --loglevel=info

Usage (combined worker + beat):
    celery -A celery_worker.celery worker --beat --loglevel=info
"""

from dotenv import load_dotenv

load_dotenv()

from celery import Celery
from celery.schedules import crontab
from app import create_app

flask_app = create_app()

celery = Celery(flask_app.name)
celery.conf.update(
    broker_url=flask_app.config["CELERY_BROKER_URL"],
    result_backend=flask_app.config["CELERY_RESULT_BACKEND"],
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution limits
    task_soft_time_limit=300,  # 5 min soft limit
    task_time_limit=600,       # 10 min hard limit
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Celery Beat periodic task schedule
    beat_schedule={
        "wearable-sync-all-users": {
            "task": "app.tasks.wearable_tasks.sync_all_active_connections",
            "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
            "options": {"queue": "wearables"},
        },
        "daily-insight-generation": {
            "task": "app.tasks.wearable_tasks.generate_daily_insights",
            "schedule": crontab(minute=30, hour=2),  # Daily at 02:30 UTC
            "options": {"queue": "insights"},
        },
        "weekly-microbiome-reanalysis": {
            "task": "app.tasks.microbiome_tasks.schedule_weekly_reanalysis",
            "schedule": crontab(minute=0, hour=3, day_of_week=1),  # Monday 03:00 UTC
            "options": {"queue": "analysis"},
        },
    },
    # Route tasks to queues
    task_routes={
        "app.tasks.wearable_tasks.*": {"queue": "wearables"},
        "app.tasks.genome_tasks.*": {"queue": "analysis"},
        "app.tasks.epigenetics_tasks.*": {"queue": "analysis"},
        "app.tasks.blood_tasks.*": {"queue": "analysis"},
        "app.tasks.microbiome_tasks.*": {"queue": "analysis"},
    },
    # Default queue for unmatched tasks
    task_default_queue="default",
)


class FlaskTask(celery.Task):
    """Ensure every Celery task runs inside a Flask application context."""

    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)


celery.Task = FlaskTask

# Import task modules so Celery discovers them
import app.tasks  # noqa: F401, E402
