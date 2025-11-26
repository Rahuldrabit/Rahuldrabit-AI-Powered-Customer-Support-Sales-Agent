"""Webhook endpoints for TikTok and LinkedIn."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.dependencies import get_db
from app.models.schemas import TikTokWebhook, LinkedInWebhook
from app.models.database import Platform
from app.services.message_processor import process_incoming_message
from app.services.tasks import process_incoming_message_task
from fastapi import Header
from app.utils.logger import log

router = APIRouter()


@router.post("/tiktok")
async def tiktok_webhook(
    webhook_data: TikTokWebhook,
    db: Session = Depends(get_db),
    x_signature: str | None = Header(default=None)
):
    """
    Receive TikTok DM webhook events.
    
    Args:
        webhook_data: TikTok webhook payload
        db: Database session
        
    Returns:
        Success response
    """
    log.info(f"Received TikTok webhook: {webhook_data.event_type}")
    
    try:
        # Require signature
        from app.integrations.tiktok import TikTokClient
        client = TikTokClient()
        if not x_signature:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature header")
        if not client.verify_webhook_signature(payload=webhook_data.model_dump_json(), signature=x_signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

        # Enqueue for async processing via Celery
        process_incoming_message_task.delay(
            platform=Platform.TIKTOK.value,
            platform_user_id=webhook_data.user_id,
            platform_conversation_id=webhook_data.conversation_id,
            message_content=webhook_data.message,
            username=None,
            extra_payload={"media_url": webhook_data.media_url} if webhook_data.media_url else None,
        )
        
        return {"status": "accepted"}
        
    except Exception as e:
        log.error(f"Error processing TikTok webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


@router.post("/linkedin")
async def linkedin_webhook(
    webhook_data: LinkedInWebhook,
    db: Session = Depends(get_db),
    x_signature: str | None = Header(default=None)
):
    """
    Receive LinkedIn messaging webhook events.
    
    Args:
        webhook_data: LinkedIn webhook payload
        db: Database session
        
    Returns:
        Success response
    """
    log.info(f"Received LinkedIn webhook: {webhook_data.event_type}")
    
    try:
        # Require signature
        from app.integrations.linkedin import LinkedInClient
        client = LinkedInClient()
        if not x_signature:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature header")
        if not client.verify_webhook_signature(payload=webhook_data.model_dump_json(), signature=x_signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

        # Enqueue for async processing via Celery
        extra = {"attachments": webhook_data.attachments} if webhook_data.attachments else None
        process_incoming_message_task.delay(
            platform=Platform.LINKEDIN.value,
            platform_user_id=webhook_data.sender_id,
            platform_conversation_id=webhook_data.conversation_id,
            message_content=webhook_data.message_text,
            username=None,
            extra_payload=extra,
        )
        
        return {"status": "accepted"}
        
    except Exception as e:
        log.error(f"Error processing LinkedIn webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


@router.get("/verify")
async def verify_webhook(challenge: str = None):
    """
    Webhook verification endpoint for platform setup.
    
    Args:
        challenge: Challenge string from platform
        
    Returns:
        Challenge response
    """
    if challenge:
        return {"challenge": challenge}
    return {"status": "webhook endpoint ready"}
