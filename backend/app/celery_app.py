"""
Configuración de Celery para procesamiento asíncrono.
Broker y backend: Redis (configurado via REDIS_URL en .env).
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "reconcilaapp",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Bogota",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,        # resultados expiran en 1 hora
)
