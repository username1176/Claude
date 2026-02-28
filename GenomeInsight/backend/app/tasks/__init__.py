"""Celery task modules.

Import all task submodules here so that ``celery_worker.py``'s
``import app.tasks`` causes Celery to discover all ``@shared_task``
functions.
"""

from app.tasks.genome_tasks import run_genome_analysis  # noqa: F401
from app.tasks.blood_tasks import run_blood_change_analysis  # noqa: F401
from app.tasks.epigenetics_tasks import run_epigenetics_analysis  # noqa: F401
from app.tasks.wearable_tasks import (  # noqa: F401
    sync_wearable_connection,
    sync_all_active_connections,
    generate_daily_insights,
)
from app.tasks.microbiome_tasks import (  # noqa: F401
    run_microbiome_analysis,
    schedule_weekly_reanalysis,
    check_and_reanalyze_stale,
)
