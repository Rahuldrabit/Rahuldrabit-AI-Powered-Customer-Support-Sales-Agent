"""Message handling endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.dependencies import get_db
from app.models.schemas import (
    SendMessageRequest,
    SendMessageResponse,
    ConversationResponse,
    MessageResponse
)
from app.models.database import Conversation, Message, User, Platform, ConversationStatus
from app.services.message_processor import send_message_to_platform
from app.utils.logger import log
from app.utils.exceptions import ConversationNotFoundError

router = APIRouter()


@router.post("/send", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    db: Session = Depends(get_db)
):
    """
    Send a message to a platform.
    
    Args:
        request: Send message request
        db: Database session
        
    Returns:
        Send message response
    """
    log.info(f"Sending message to conversation {request.conversation_id}")
    
    try:
        # Get conversation
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id
        ).first()
        
        if not conversation:
            raise ConversationNotFoundError(request.conversation_id)
        
        # Send message via platform integration
        platform = Platform(request.platform)
        success = await send_message_to_platform(
            platform=platform,
            conversation_id=conversation.platform_conversation_id,
            message=request.message,
            db=db
        )
        
        if success:
            # Save message to database
            from app.models.database import MessageSender as _MsgSender
            message = Message(
                conversation_id=conversation.id,
                sender_type=_MsgSender.AGENT,
                content=request.message
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            
            return SendMessageResponse(
                success=True,
                message_id=message.id
            )
        else:
            return SendMessageResponse(
                success=False,
                error="Failed to send message to platform"
            )
            
    except ConversationNotFoundError:
        raise
    except Exception as e:
        log.error(f"Error sending message: {e}")
        return SendMessageResponse(
            success=False,
            error=str(e)
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Get conversation details with message history.
    
    Args:
        conversation_id: Conversation ID
        db: Database session
        
    Returns:
        Conversation details
    """
    log.info(f"Retrieving conversation {conversation_id}")
    
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        raise ConversationNotFoundError(conversation_id)
    
    return conversation


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    escalated: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """
    List all conversations with optional filters.
    
    Args:
        platform: Filter by platform (tiktok/linkedin)
        status: Filter by status (active/escalated/closed)
        escalated: Filter by escalation status
        limit: Maximum number of results
        offset: Pagination offset
        db: Database session
        
    Returns:
        List of conversations
    """
    log.info(f"Listing conversations (platform={platform}, status={status})")
    
    query = db.query(Conversation)
    
    # Apply filters using enums where possible
    if platform:
        try:
            platform_enum = Platform(platform)
            query = query.filter(Conversation.platform == platform_enum)
        except ValueError:
            # Invalid platform string, return empty list
            return []
    if status:
        try:
            status_enum = ConversationStatus(status)
            query = query.filter(Conversation.status == status_enum)
        except ValueError:
            return []
    if escalated is not None:
        query = query.filter(Conversation.escalated == escalated)
    
    # Order by most recent
    query = query.order_by(desc(Conversation.updated_at))
    
    # Pagination
    conversations = query.offset(offset).limit(limit).all()
    
    return conversations
