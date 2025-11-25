"""Custom exceptions for the application."""

from fastapi import HTTPException, status


class AgentException(Exception):
    """Base exception for agent-related errors."""
    pass


class ConversationNotFoundError(HTTPException):
    """Exception raised when a conversation is not found."""
    def __init__(self, conversation_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )


class MessageNotFoundError(HTTPException):
    """Exception raised when a message is not found."""
    def __init__(self, message_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found"
        )


class PlatformAPIError(Exception):
    """Exception raised when platform API calls fail."""
    pass


class RateLimitExceededError(HTTPException):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, platform: str):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {platform}"
        )


class InvalidConfigurationError(Exception):
    """Exception raised when configuration is invalid."""
    pass
