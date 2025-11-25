"""Message processing service."""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import time

from app.models.database import (
    User, Conversation, Message, Platform,
    ConversationStatus, MessageSender, MessageIntent
)
from app.agent.graph import get_agent
from app.integrations.tiktok import TikTokClient
from app.integrations.linkedin import LinkedInClient
from app.utils.logger import log


async def process_incoming_message(
    db: Session,
    platform: Platform,
    platform_user_id: str,
    platform_conversation_id: str,
    message_content: str,
    username: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process an incoming message from a platform.
    
    Args:
        db: Database session
        platform: Platform enum (TikTok/LinkedIn)
        platform_user_id: Platform-specific user ID
        platform_conversation_id: Platform-specific conversation ID
        message_content: Message content
        username: Optional username
        
    Returns:
        Processing result with message ID and response status
    """
    start_time = time.time()
    
    log.info(f"Processing incoming message from {platform.value}: {message_content[:50]}...")
    
    # Get or create user
    user = db.query(User).filter(
        User.platform_user_id == platform_user_id
    ).first()
    
    if not user:
        user = User(
            platform=platform,
            platform_user_id=platform_user_id,
            username=username
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        log.info(f"Created new user: {platform_user_id}")
    
    # Get or create conversation
    conversation = db.query(Conversation).filter(
        Conversation.platform_conversation_id == platform_conversation_id
    ).first()
    
    if not conversation:
        conversation = Conversation(
            user_id=user.id,
            platform=platform,
            platform_conversation_id=platform_conversation_id,
            status=ConversationStatus.ACTIVE
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        log.info(f"Created new conversation: {platform_conversation_id}")
    
    # Save incoming message
    incoming_message = Message(
        conversation_id=conversation.id,
        sender_type=MessageSender.USER,
        content=message_content
    )
    db.add(incoming_message)
    db.commit()
    db.refresh(incoming_message)
    
    # Get conversation history
    conversation_history = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at).all()
    
    # Format history for agent
    history = [
        {
            "sender_type": msg.sender_type.value,
            "content": msg.content
        }
        for msg in conversation_history[:-1]  # Exclude the current message
    ]
    
    # Process with agent
    agent = get_agent()
    agent_result = agent.process_message(
        message=message_content,
        conversation_history=history
    )
    
    log.info(f"Agent processing complete. Intent: {agent_result.get('intent')}")
    
    # Calculate response time
    response_time_ms = int((time.time() - start_time) * 1000)
    
    # Handle escalation
    if agent_result.get("requires_escalation"):
        conversation.escalated = True
        conversation.escalation_reason = agent_result.get("escalation_reason", "Unknown")
        conversation.status = ConversationStatus.ESCALATED
        db.commit()
        log.warning(f"Conversation {conversation.id} escalated: {conversation.escalation_reason}")
    
    # Save agent response
    response_message = Message(
        conversation_id=conversation.id,
        sender_type=MessageSender.AGENT,
        content=agent_result.get("response", ""),
        intent=MessageIntent(agent_result.get("intent", "general")),
        sentiment_score=agent_result.get("sentiment_score"),
        response_time_ms=response_time_ms
    )
    db.add(response_message)
    db.commit()
    db.refresh(response_message)
    
    # Send response to platform (if not escalated or send escalation message)
    response_sent = False
    if agent_result.get("response"):
        response_sent = await send_message_to_platform(
            platform=platform,
            conversation_id=platform_conversation_id,
            message=agent_result.get("response"),
            db=db
        )
    
    return {
        "message_id": incoming_message.id,
        "response_id": response_message.id,
        "intent": agent_result.get("intent"),
        "requires_escalation": agent_result.get("requires_escalation"),
        "response_sent": response_sent,
        "response_time_ms": response_time_ms
    }


async def send_message_to_platform(
    platform: Platform,
    conversation_id: str,
    message: str,
    db: Session
) -> bool:
    """
    Send a message to a platform.
    
    Args:
        platform: Platform enum
        conversation_id: Platform-specific conversation ID
        message: Message to send
        db: Database session
        
    Returns:
        True if successful, False otherwise
    """
    log.info(f"Sending message to {platform.value}")
    
    try:
        if platform == Platform.TIKTOK:
            client = TikTokClient()
            return await client.send_message(conversation_id, message)
        elif platform == Platform.LINKEDIN:
            client = LinkedInClient()
            return await client.send_message(conversation_id, message)
        else:
            log.error(f"Unknown platform: {platform}")
            return False
            
    except Exception as e:
        log.error(f"Error sending message to {platform.value}: {e}")
        return False
