"""TikTok API integration (Mock implementation for development)."""

from typing import Optional
import asyncio
from app.config import settings
from app.utils.logger import log


class TikTokClient:
    """
    TikTok API client for sending messages.
    
    This is a mock implementation for development. In production,
    this would integrate with the actual TikTok API.
    """
    
    def __init__(self):
        """Initialize TikTok client."""
        self.client_key = settings.tiktok_client_key
        self.client_secret = settings.tiktok_client_secret
        self.webhook_secret = settings.tiktok_webhook_secret
        self.rate_limit = settings.tiktok_rate_limit
    
    async def send_message(
        self,
        conversation_id: str,
        message: str,
        media_url: Optional[str] = None
    ) -> bool:
        """
        Send a message via TikTok API.
        
        Args:
            conversation_id: TikTok conversation ID
            message: Message content
            media_url: Optional media attachment URL
            
        Returns:
            True if successful, False otherwise
        """
        log.info(f"[MOCK] Sending TikTok message to {conversation_id}: {message[:50]}...")
        
        # Mock implementation - simulate API call delay
        await asyncio.sleep(0.1)
        
        # In production, this would make an actual API call:
        # POST https://open-api.tiktok.com/v1/message/send/
        # Headers: Authorization: Bearer {access_token}
        # Body: {
        #   "conversation_id": conversation_id,
        #   "message_text": message,
        #   "media_url": media_url (optional)
        # }
        
        log.info(f"[MOCK] TikTok message sent successfully")
        return True
    
    async def get_user_info(self, user_id: str) -> dict:
        """
        Get TikTok user information.
        
        Args:
            user_id: TikTok user ID
            
        Returns:
            User information dictionary
        """
        log.info(f"[MOCK] Getting TikTok user info for {user_id}")
        
        await asyncio.sleep(0.1)
        
        return {
            "user_id": user_id,
            "username": f"tiktok_user_{user_id[-4:]}",
            "display_name": f"TikTok User {user_id[-4:]}"
        }
    
    def verify_webhook_signature(
        self,
        payload: str,
        signature: str
    ) -> bool:
        """
        Verify TikTok webhook signature.
        
        Args:
            payload: Webhook payload
            signature: Signature from headers
            
        Returns:
            True if valid, False otherwise
        """
        # In production, implement signature verification
        # using HMAC-SHA256 with webhook_secret
        return True
