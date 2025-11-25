"""Analytics endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from datetime import datetime, timedelta

from app.api.dependencies import get_db
from app.models.schemas import (
    MetricsResponse,
    ConversationInsightsResponse,
    ConversationInsight,
    EscalationStats
)
from app.models.database import Message, Conversation, Analytics
from app.utils.logger import log

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get overall system metrics.
    
    Args:
        start_date: Start date for metrics
        end_date: End date for metrics
        db: Database session
        
    Returns:
        System metrics
    """
    log.info("Retrieving system metrics")
    
    # Default to last 30 days
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Calculate average response time
    avg_response_time = db.query(func.avg(Message.response_time_ms)).filter(
        Message.sender_type == "agent",
        Message.created_at >= start_date,
        Message.created_at <= end_date,
        Message.response_time_ms.isnot(None)
    ).scalar() or 0.0
    
    # Total messages
    total_messages = db.query(func.count(Message.id)).filter(
        Message.created_at >= start_date,
        Message.created_at <= end_date
    ).scalar()
    
    # Total conversations
    total_conversations = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= start_date,
        Conversation.created_at <= end_date
    ).scalar()
    
    # Escalation rate
    total_escalations = db.query(func.count(Conversation.id)).filter(
        Conversation.escalated == True,
        Conversation.created_at >= start_date,
        Conversation.created_at <= end_date
    ).scalar()
    
    escalation_rate = (total_escalations / total_conversations * 100) if total_conversations > 0 else 0.0
    
    # Average sentiment
    avg_sentiment = db.query(func.avg(Message.sentiment_score)).filter(
        Message.sentiment_score.isnot(None),
        Message.created_at >= start_date,
        Message.created_at <= end_date
    ).scalar()
    
    return MetricsResponse(
        average_response_time_ms=round(avg_response_time, 2),
        total_messages=total_messages,
        total_conversations=total_conversations,
        escalation_rate=round(escalation_rate, 2),
        average_sentiment=round(avg_sentiment, 2) if avg_sentiment else None
    )


@router.get("/conversations", response_model=ConversationInsightsResponse)
async def get_conversation_insights(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get conversation insights grouped by intent.
    
    Args:
        start_date: Start date for insights
        end_date: End date for insights
        db: Database session
        
    Returns:
        Conversation insights
    """
    log.info("Retrieving conversation insights")
    
    # Default to last 30 days
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Get intent distribution
    intent_counts = db.query(
        Message.intent,
        func.count(Message.id).label('count')
    ).filter(
        Message.intent.isnot(None),
        Message.created_at >= start_date,
        Message.created_at <= end_date
    ).group_by(Message.intent).all()
    
    total = sum([count for _, count in intent_counts])
    
    insights = [
        ConversationInsight(
            intent=intent,
            count=count,
            percentage=round((count / total * 100) if total > 0 else 0, 2)
        )
        for intent, count in intent_counts
    ]
    
    return ConversationInsightsResponse(
        insights=insights,
        total_conversations=total
    )


@router.get("/escalations", response_model=EscalationStats)
async def get_escalation_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get escalation statistics.
    
    Args:
        start_date: Start date for statistics
        end_date: End date for statistics
        db: Database session
        
    Returns:
        Escalation statistics
    """
    log.info("Retrieving escalation statistics")
    
    # Default to last 30 days
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Total escalations
    total_escalations = db.query(func.count(Conversation.id)).filter(
        Conversation.escalated == True,
        Conversation.created_at >= start_date,
        Conversation.created_at <= end_date
    ).scalar()
    
    # Total conversations
    total_conversations = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= start_date,
        Conversation.created_at <= end_date
    ).scalar()
    
    escalation_rate = (total_escalations / total_conversations * 100) if total_conversations > 0 else 0.0
    
    # Top escalation reasons
    reasons = db.query(
        Conversation.escalation_reason,
        func.count(Conversation.id).label('count')
    ).filter(
        Conversation.escalated == True,
        Conversation.escalation_reason.isnot(None),
        Conversation.created_at >= start_date,
        Conversation.created_at <= end_date
    ).group_by(Conversation.escalation_reason).order_by(desc('count')).limit(5).all()
    
    top_reasons = [
        {"reason": reason, "count": count}
        for reason, count in reasons
    ]
    
    return EscalationStats(
        total_escalations=total_escalations,
        escalation_rate=round(escalation_rate, 2),
        top_reasons=top_reasons
    )
