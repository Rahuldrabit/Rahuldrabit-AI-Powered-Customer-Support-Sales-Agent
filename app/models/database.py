"""Database models using SQLAlchemy."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import enum

from app.config import settings

# Create database engine
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class ConversationStatus(str, enum.Enum):
    """Conversation status enumeration."""
    ACTIVE = "active"
    ESCALATED = "escalated"
    CLOSED = "closed"


class Platform(str, enum.Enum):
    """Platform enumeration."""
    TIKTOK = "tiktok"
    LINKEDIN = "linkedin"


class MessageSender(str, enum.Enum):
    """Message sender type enumeration."""
    USER = "user"
    AGENT = "agent"
    HUMAN = "human"


class MessageIntent(str, enum.Enum):
    """Message intent classification."""
    SUPPORT = "support"
    SALES = "sales"
    GENERAL = "general"
    URGENT = "urgent"


# Database Models

class User(Base):
    """User model for platform-specific user profiles."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(SQLEnum(Platform), nullable=False)
    platform_user_id = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    profile_url = Column(String, nullable=True)
    metadata = Column(Text, nullable=True)  # JSON stored as text
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    conversations = relationship("Conversation", back_populates="user")


class Conversation(Base):
    """Conversation model for tracking message threads."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    platform = Column(SQLEnum(Platform), nullable=False)
    platform_conversation_id = Column(String, unique=True, nullable=False, index=True)
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ACTIVE)
    escalated = Column(Boolean, default=False)
    escalation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Message model for individual messages in conversations."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_type = Column(SQLEnum(MessageSender), nullable=False)
    content = Column(Text, nullable=False)
    intent = Column(SQLEnum(MessageIntent), nullable=True)
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0
    response_time_ms = Column(Integer, nullable=True)
    metadata = Column(Text, nullable=True)  # JSON stored as text
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class AgentConfig(Base):
    """Agent configuration model for storing prompts and rules."""
    __tablename__ = "agent_configs"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String, unique=True, nullable=False, index=True)
    config_value = Column(Text, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Analytics(Base):
    """Analytics model for storing metrics and insights."""
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, index=True)
    metric_type = Column(String, nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    dimension = Column(String, nullable=True)  # e.g., platform, intent
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metadata = Column(Text, nullable=True)  # JSON stored as text


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
