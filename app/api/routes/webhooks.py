"""Webhook endpoints for TikTok and LinkedIn."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.dependencies import get_db
from app.models.schemas import TikTokWebhook, LinkedInWebhook
from app.models.database import Platform
from app.services.message_processor import process_incoming_message
from app.utils.logger import log

router = APIRouter()


@router.post("/tiktok")
async def tiktok_webhook(
    webhook_data: TikTokWebhook,
    db: Session = Depends(get_db)
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
        # Process the incoming message
        result = await process_incoming_message(
            db=db,
            platform=Platform.TIKTOK,
            platform_user_id=webhook_data.user_id,
            platform_conversation_id=webhook_data.conversation_id,
            message_content=webhook_data.message,
            username=None  # TikTok may provide this in metadata
        )
        
        log.info(f"TikTok message processed: {result.get('message_id')}")
        
        return {
            "status": "success",
            "message_id": result.get("message_id"),
            "response_sent": result.get("response_sent", False)
        }
        
    except Exception as e:
        log.error(f"Error processing TikTok webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


@router.post("/linkedin")
async def linkedin_webhook(
    webhook_data: LinkedInWebhook,
    db: Session = Depends(get_db)
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
        # Process the incoming message
        result = await process_incoming_message(
            db=db,
            platform=Platform.LINKEDIN,
            platform_user_id=webhook_data.sender_id,
            platform_conversation_id=webhook_data.conversation_id,
            message_content=webhook_data.message_text,
            username=None  # LinkedIn may provide this in metadata
        )
        
        log.info(f"LinkedIn message processed: {result.get('message_id')}")
        
        return {
            "status": "success",
            "message_id": result.get("message_id"),
            "response_sent": result.get("response_sent", False)
        }
        
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
