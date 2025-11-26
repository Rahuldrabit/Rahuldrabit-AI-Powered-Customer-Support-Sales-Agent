"""Celery tasks for asynchronous processing."""

from celery import Celery
from sqlalchemy.orm import Session
from typing import Optional

from app.config import settings
from app.models.database import SessionLocal, Platform
from app.services.message_processor import process_incoming_message
from app.utils.logger import log

# Configure Celery
celery_app = Celery(
    "agent_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)


@celery_app.task(name="process_incoming_message_task")
def process_incoming_message_task(
    platform: str,
    platform_user_id: str,
    platform_conversation_id: str,
    message_content: str,
    username: Optional[str] = None,
    extra_payload: Optional[dict] = None,
):
    """Celery task wrapper around process_incoming_message.

    Uses a fresh DB session and serializable primitives only.
    """
    log.info(
        f"[Celery] Processing message (platform={platform}, conv={platform_conversation_id})"
    )
    db: Session = SessionLocal()
    try:
        # Convert platform enum from string
        plat_enum = Platform(platform)
        # Run async service in blocking context using asyncio.run-like pattern
        # Here process_incoming_message is async; Celery tasks are sync, so we use asyncio loop
        import asyncio
        asyncio.run(
            process_incoming_message(
                db=db,
                platform=plat_enum,
                platform_user_id=platform_user_id,
                platform_conversation_id=platform_conversation_id,
                message_content=message_content,
                extra_payload=extra_payload,
                username=username,
            )
        )
        log.info("[Celery] Message processed successfully")
        return {"status": "ok"}
    except Exception as e:
        log.error(f"[Celery] Error processing message: {e}")
        return {"status": "error", "detail": str(e)}
    finally:
        db.close()
