"""Pydantic schemas for request/response validation."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# User Schemas

class UserBase(BaseModel):
    """Base user schema."""
    platform: str
    platform_user_id: str
    username: Optional[str] = None
    display_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user."""
    pass


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Message Schemas

class MessageBase(BaseModel):
    """Base message schema."""
    content: str
    sender_type: str


class MessageCreate(MessageBase):
    """Schema for creating a message."""
    conversation_id: int
    intent: Optional[str] = None
    sentiment_score: Optional[float] = None


class MessageResponse(MessageBase):
    """Schema for message response."""
    id: int
    conversation_id: int
    intent: Optional[str] = None
    sentiment_score: Optional[float] = None
    response_time_ms: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# Conversation Schemas

class ConversationBase(BaseModel):
    """Base conversation schema."""
    platform: str


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation."""
    user_id: int
    platform_conversation_id: str


class ConversationResponse(ConversationBase):
    """Schema for conversation response."""
    id: int
    user_id: int
    platform_conversation_id: str
    status: str
    escalated: bool
    escalation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    messages: List[MessageResponse] = []

    model_config = {"from_attributes": True}


# Webhook Schemas

class WebhookMessage(BaseModel):
    """Schema for incoming webhook messages."""
    platform_user_id: str
    conversation_id: str
    message_content: str
    username: Optional[str] = None
    timestamp: Optional[datetime] = None


class TikTokWebhook(BaseModel):
    """Schema for TikTok webhook payload."""
    event_type: str
    user_id: str
    message: str
    conversation_id: str
    timestamp: Optional[int] = None


class LinkedInWebhook(BaseModel):
    """Schema for LinkedIn webhook payload."""
    event_type: str
    sender_id: str
    message_text: str
    conversation_id: str
    timestamp: Optional[int] = None


# Response Schemas

class SendMessageRequest(BaseModel):
    """Schema for sending messages."""
    conversation_id: int
    platform: str
    message: str


class SendMessageResponse(BaseModel):
    """Schema for send message response."""
    success: bool
    message_id: Optional[int] = None
    error: Optional[str] = None


# Agent Schemas

class AgentConfigRequest(BaseModel):
    """Schema for agent configuration request."""
    config_key: str
    config_value: str
    description: Optional[str] = None


class AgentConfigResponse(BaseModel):
    """Schema for agent configuration response."""
    id: int
    config_key: str
    config_value: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentStatusResponse(BaseModel):
    """Schema for agent status response."""
    status: str
    uptime_seconds: Optional[float] = None
    total_conversations: int = 0
    active_conversations: int = 0
    escalated_conversations: int = 0


# Analytics Schemas

class MetricsResponse(BaseModel):
    """Schema for metrics response."""
    average_response_time_ms: float
    total_messages: int
    total_conversations: int
    escalation_rate: float
    average_sentiment: Optional[float] = None


class ConversationInsight(BaseModel):
    """Schema for conversation insights."""
    intent: str
    count: int
    percentage: float


class ConversationInsightsResponse(BaseModel):
    """Schema for conversation insights response."""
    insights: List[ConversationInsight]
    total_conversations: int


class EscalationStats(BaseModel):
    """Schema for escalation statistics."""
    total_escalations: int
    escalation_rate: float
    top_reasons: List[dict]


# Admin Schemas

class EscalateRequest(BaseModel):
    """Schema for manual escalation request."""
    reason: str


class OverrideMessageRequest(BaseModel):
    """Schema for overriding AI response."""
    new_content: str
    reason: Optional[str] = None
