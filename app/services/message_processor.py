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
from app.services.analytics import AnalyticsService
from app.config import settings
import json


async def process_incoming_message(
    db: Session,
    platform: Platform,
    platform_user_id: str,
    platform_conversation_id: str,
    message_content: str,
    extra_payload: Optional[Dict[str, Any]] = None,
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

    # Ensure sticky A/B variant stored per user when using auto/random mode
    try:
        from app.agent.tools import assign_sticky_ab_variant
        sticky_modes = {"random", "auto"}
        desired_mode = (settings.agent_prompt_variant or "").strip().lower()
        if desired_mode in sticky_modes:
            # read extra_data JSON, assign if missing
            extra = {}
            if getattr(user, 'extra_data', None):
                try:
                    extra = json.loads(user.extra_data)
                except Exception:
                    extra = {}
            if 'ab_variant' not in extra:
                extra['ab_variant'] = assign_sticky_ab_variant(platform_user_id)
                user.extra_data = json.dumps(extra)
                db.commit()
    except Exception as e:
        log.error(f"Failed to set sticky A/B variant: {e}")
    
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
    import json as _json
    extra_json = None
    if extra_payload:
        try:
            extra_json = _json.dumps(extra_payload)
        except Exception:
            extra_json = None

    incoming_message = Message(
        conversation_id=conversation.id,
        sender_type=MessageSender.USER,
        content=message_content,
        extra_data=extra_json
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
    # Load user sticky variant if any
    sticky_variant = None
    try:
        extra = {}
        if getattr(user, 'extra_data', None):
            extra = json.loads(user.extra_data)
        sticky_variant = extra.get('ab_variant')
    except Exception:
        sticky_variant = None

    agent_result = agent.process_message(
        message=message_content,
        conversation_history=history,
        sticky_prompt_variant=sticky_variant,
        platform=platform.value,
        platform_user_id=platform_user_id,
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
    
    # Record A/B testing metric for prompt variant (store 1 for valid response, 0 otherwise)
    try:
        variant = agent_result.get("prompt_variant", settings.agent_prompt_variant.upper() if hasattr(settings, 'agent_prompt_variant') else 'A')
        response_valid = agent_result.get("metadata", {}).get("response_valid", True)
        metrics = AnalyticsService(db)
        metrics.store_metric(metric_type="ab_test", metric_value=1.0 if response_valid else 0.0, dimension=variant)
    except Exception as e:
        log.error(f"Failed to store A/B metric: {e}")
    
    # Send response to platform (if not escalated or send escalation message)
    response_sent = False
    if agent_result.get("response"):
        # Attempt to extract media/attachments for outbound
        outbound_media = None
        try:
            if extra_payload and isinstance(extra_payload, dict):
                outbound_media = extra_payload.get("media_url")
        except Exception:
            outbound_media = None
        response_sent = await send_message_to_platform(
            platform=platform,
            conversation_id=platform_conversation_id,
            message=agent_result.get("response"),
            db=db,
            media_url=outbound_media
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
    db: Session,
    media_url: Optional[str] = None,
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
        # Retrieve OAuth credentials if available
        access_token = None
        try:
            from app.models.database import Conversation as _Conv, Credentials as _Cred
            conv = db.query(_Conv).filter(_Conv.platform_conversation_id == conversation_id).first()
            if conv:
                cred = db.query(_Cred).filter(_Cred.user_id == conv.user_id, _Cred.platform == platform).order_by(_Cred.updated_at.desc()).first()
                if cred:
                    access_token = cred.access_token
        except Exception:
            access_token = None
        if platform == Platform.TIKTOK:
            client = TikTokClient()
            return await client.send_message(conversation_id, message, media_url=media_url, access_token=access_token)
        elif platform == Platform.LINKEDIN:
            client = LinkedInClient()
            return await client.send_message(conversation_id, message, access_token=access_token)
        else:
            log.error(f"Unknown platform: {platform}")
            return False
            
    except Exception as e:
        log.error(f"Error sending message to {platform.value}: {e}")
        return False
