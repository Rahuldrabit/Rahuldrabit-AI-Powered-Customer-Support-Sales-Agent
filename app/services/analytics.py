"""Analytics service for collecting and calculating metrics."""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.models.database import Message, Conversation, Analytics
from app.utils.logger import log


class AnalyticsService:
    """Service for analytics and metrics."""
    
    def __init__(self, db: Session):
        """Initialize the analytics service."""
        self.db = db
    
    def calculate_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate system metrics for a date range."""
        log.info(f"Calculating metrics from {start_date} to {end_date}")
        
        # Average response time
        avg_response_time = self.db.query(func.avg(Message.response_time_ms)).filter(
            Message.sender_type == "agent",
            Message.created_at >= start_date,
            Message.created_at <= end_date,
            Message.response_time_ms.isnot(None)
        ).scalar() or 0.0
        
        # Total messages
        total_messages = self.db.query(func.count(Message.id)).filter(
            Message.created_at >= start_date,
            Message.created_at <= end_date
        ).scalar()
        
        # Total conversations
        total_conversations = self.db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= start_date,
            Conversation.created_at <= end_date
        ).scalar()
        
        # Escalation rate
        total_escalations = self.db.query(func.count(Conversation.id)).filter(
            Conversation.escalated == True,
            Conversation.created_at >= start_date,
            Conversation.created_at <= end_date
        ).scalar()
        
        escalation_rate = (total_escalations / total_conversations * 100) if total_conversations > 0 else 0.0
        
        # Average sentiment
        avg_sentiment = self.db.query(func.avg(Message.sentiment_score)).filter(
            Message.sentiment_score.isnot(None),
            Message.created_at >= start_date,
            Message.created_at <= end_date
        ).scalar()
        
        return {
            "average_response_time_ms": round(avg_response_time, 2),
            "total_messages": total_messages,
            "total_conversations": total_conversations,
            "escalation_rate": round(escalation_rate, 2),
            "average_sentiment": round(avg_sentiment, 2) if avg_sentiment else None
        }
    
    def store_metric(
        self,
        metric_type: str,
        metric_value: float,
        dimension: str = None
    ) -> None:
        """Store a metric in the analytics table."""
        metric = Analytics(
            metric_type=metric_type,
            metric_value=metric_value,
            dimension=dimension
        )
        self.db.add(metric)
        self.db.commit()
    
    def get_intent_distribution(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get distribution of message intents."""
        results = self.db.query(
            Message.intent,
            func.count(Message.id).label('count')
        ).filter(
            Message.intent.isnot(None),
            Message.created_at >= start_date,
            Message.created_at <= end_date
        ).group_by(Message.intent).all()
        
        total = sum([count for _, count in results])
        
        return [
            {
                "intent": intent.value if intent else "unknown",
                "count": count,
                "percentage": round((count / total * 100) if total > 0 else 0, 2)
            }
            for intent, count in results
        ]
