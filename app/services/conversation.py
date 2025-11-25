"""Conversation service for managing conversations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database import Conversation, Message, ConversationStatus
from app.utils.logger import log


class ConversationService:
    """Service for managing conversations."""
    
    def __init__(self, db: Session):
        """Initialize the conversation service."""
        self.db = db
    
    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
    
    def get_conversations(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        escalated: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Conversation]:
        """Get conversations with filters."""
        query = self.db.query(Conversation)
        
        if platform:
            query = query.filter(Conversation.platform == platform)
        if status:
            query = query.filter(Conversation.status == status)
        if escalated is not None:
            query = query.filter(Conversation.escalated == escalated)
        
        return query.offset(offset).limit(limit).all()
    
    def close_conversation(self, conversation_id: int) -> bool:
        """Close a conversation."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        conversation.status = ConversationStatus.CLOSED
        conversation.closed_at = datetime.utcnow()
        conversation.updated_at = datetime.utcnow()
        
        self.db.commit()
        log.info(f"Conversation {conversation_id} closed")
        return True
    
    def escalate_conversation(
        self,
        conversation_id: int,
        reason: str
    ) -> bool:
        """Escalate a conversation to human agent."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        conversation.escalated = True
        conversation.escalation_reason = reason
        conversation.status = ConversationStatus.ESCALATED
        conversation.updated_at = datetime.utcnow()
        
        self.db.commit()
        log.info(f"Conversation {conversation_id} escalated: {reason}")
        return True
