"""Celery worker configuration."""

from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "customer_support_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Import tasks
celery_app.conf.task_routes = {
    'app.services.celery_worker.*': {'queue': 'default'},
}
