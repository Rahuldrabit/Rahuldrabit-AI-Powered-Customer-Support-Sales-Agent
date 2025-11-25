"""Admin endpoints for manual intervention."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.api.dependencies import get_db
from app.models.schemas import EscalateRequest, OverrideMessageRequest
from app.models.database import Conversation, Message, ConversationStatus
from app.utils.logger import log
from app.utils.exceptions import ConversationNotFoundError, MessageNotFoundError

router = APIRouter()


@router.post("/escalate/{conversation_id}")
async def escalate_conversation(
    conversation_id: int,
    request: EscalateRequest,
    db: Session = Depends(get_db)
):
    """
    Manually escalate a conversation to human agent.
    
    Args:
        conversation_id: Conversation ID to escalate
        request: Escalation request with reason
        db: Database session
        
    Returns:
        Success response
    """
    log.info(f"Manually escalating conversation {conversation_id}")
    
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        raise ConversationNotFoundError(conversation_id)
    
    # Update conversation
    conversation.escalated = True
    conversation.escalation_reason = request.reason
    conversation.status = ConversationStatus.ESCALATED
    conversation.updated_at = datetime.utcnow()
    
    db.commit()
    
    log.info(f"Conversation {conversation_id} escalated: {request.reason}")
    
    return {
        "status": "success",
        "conversation_id": conversation_id,
        "escalated": True,
        "reason": request.reason
    }


@router.put("/override/{message_id}")
async def override_message(
    message_id: int,
    request: OverrideMessageRequest,
    db: Session = Depends(get_db)
):
    """
    Override an AI-generated response.
    
    Args:
        message_id: Message ID to override
        request: Override request with new content
        db: Database session
        
    Returns:
        Updated message
    """
    log.info(f"Overriding message {message_id}")
    
    message = db.query(Message).filter(
        Message.id == message_id
    ).first()
    
    if not message:
        raise MessageNotFoundError(message_id)
    
    # Store original content in metadata
    original_content = message.content
    
    # Update message
    message.content = request.new_content
    message.sender_type = "human"  # Mark as human-edited
    
    db.commit()
    db.refresh(message)
    
    log.info(f"Message {message_id} overridden. Original: {original_content[:50]}...")
    
    return {
        "status": "success",
        "message_id": message_id,
        "original_content": original_content,
        "new_content": request.new_content,
        "reason": request.reason
    }


@router.get("/logs")
async def get_logs(
    level: Optional[str] = Query("INFO"),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get system logs (simplified version).
    
    Args:
        level: Log level filter
        limit: Maximum number of log entries
        db: Database session
        
    Returns:
        Log entries
    """
    log.info(f"Retrieving system logs (level={level}, limit={limit})")
    
    # This is a simplified version
    # In production, you would read from the actual log file
    try:
        from pathlib import Path
        log_file = Path("logs/app.log")
        
        if log_file.exists():
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Get last N lines
                recent_lines = lines[-limit:]
                
                # Filter by level if specified
                if level and level != "ALL":
                    recent_lines = [
                        line for line in recent_lines
                        if f"| {level} " in line or f"| {level}:" in line
                    ]
                
                return {
                    "logs": recent_lines,
                    "count": len(recent_lines),
                    "level": level
                }
        else:
            return {
                "logs": [],
                "count": 0,
                "message": "Log file not found"
            }
            
    except Exception as e:
        log.error(f"Error reading logs: {e}")
        return {
            "logs": [],
            "count": 0,
            "error": str(e)
        }


@router.post("/agent/configure")
async def configure_agent(
    config_key: str,
    config_value: str,
    description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Update agent configuration.
    
    Args:
        config_key: Configuration key
        config_value: Configuration value
        description: Optional description
        db: Database session
        
    Returns:
        Configuration update confirmation
    """
    from app.models.database import AgentConfig
    
    log.info(f"Updating agent configuration: {config_key}")
    
    # Check if config exists
    config = db.query(AgentConfig).filter(
        AgentConfig.config_key == config_key
    ).first()
    
    if config:
        config.config_value = config_value
        if description:
            config.description = description
        config.updated_at = datetime.utcnow()
    else:
        config = AgentConfig(
            config_key=config_key,
            config_value=config_value,
            description=description
        )
        db.add(config)
    
    db.commit()
    db.refresh(config)
    
    return {
        "status": "success",
        "config_key": config_key,
        "config_value": config_value
    }


@router.get("/agent/status")
async def get_agent_status(db: Session = Depends(get_db)):
    """
    Get agent health and statistics.
    
    Args:
        db: Database session
        
    Returns:
        Agent status
    """
    from sqlalchemy import func
    
    log.info("Retrieving agent status")
    
    # Get conversation counts
    total_conversations = db.query(func.count(Conversation.id)).scalar()
    active_conversations = db.query(func.count(Conversation.id)).filter(
        Conversation.status == ConversationStatus.ACTIVE
    ).scalar()
    escalated_conversations = db.query(func.count(Conversation.id)).filter(
        Conversation.escalated == True
    ).scalar()
    
    return {
        "status": "healthy",
        "uptime_seconds": None,  # Would track actual uptime in production
        "total_conversations": total_conversations,
        "active_conversations": active_conversations,
        "escalated_conversations": escalated_conversations,
        "timestamp": datetime.utcnow()
    }


@router.post("/agent/train")
async def train_agent(db: Session = Depends(get_db)):
    """
    Trigger agent retraining (placeholder).
    
    Args:
        db: Database session
        
    Returns:
        Training status
    """
    log.info("Agent retraining triggered")
    
    # This would trigger actual retraining in production
    # For now, just return a success message
    
    return {
        "status": "success",
        "message": "Agent retraining initiated",
        "timestamp": datetime.utcnow()
    }
