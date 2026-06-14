from celery import Celery
from config import settings

celery_app = Celery(
    "clipos",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["workers.pipeline"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_acks_late=True,
)