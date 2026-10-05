import logging

from celery import Celery

from packages.config.settings import settings

logger = logging.getLogger(__name__)

celery_app = Celery("ai_job_agent", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "browser.*": {"queue": "browser"},
        "job_discovery.*": {"queue": "job_discovery"},
        "application.*": {"queue": "application"},
        "document.*": {"queue": "document_processing"},
        "embeddings.*": {"queue": "embeddings"},
    },
)


@celery_app.task(name="core.health_check")  # type: ignore[untyped-decorator]
def health_check_task() -> str:
    """Basic task to verify Celery workers are functioning"""
    logger.info("Celery health check task executed successfully")
    return "OK"
