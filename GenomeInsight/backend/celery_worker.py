"""Celery worker entry point.

Usage:
    celery -A celery_worker.celery worker --loglevel=info
"""

from dotenv import load_dotenv

load_dotenv()

from celery import Celery
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
)


class FlaskTask(celery.Task):
    """Ensure every Celery task runs inside a Flask application context."""

    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)


celery.Task = FlaskTask

# Import task modules so Celery discovers them
import app.tasks  # noqa: F401, E402
