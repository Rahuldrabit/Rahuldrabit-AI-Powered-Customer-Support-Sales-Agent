"""Gemini API integration module."""

import asyncio
import time
from typing import Optional, List, Dict, Any
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.config import settings
from app.utils.logger import log


class AsyncRateLimiter:
    """Simple async rate limiter using token bucket algorithm."""
    
    def __init__(self, rate_limit: int, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            rate_limit: Number of requests allowed per time window
            time_window: Time window in seconds
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.tokens = rate_limit
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
        
    async def acquire(self):
        """Acquire a token, waiting if necessary."""
        async with self.lock:
            now = time.monotonic()
            time_passed = now - self.last_update
            
            # Refill tokens
            self.tokens = min(
                self.rate_limit,
                self.tokens + time_passed * (self.rate_limit / self.time_window)
            )
            self.last_update = now
            
            if self.tokens < 1:
                wait_time = (1 - self.tokens) * (self.time_window / self.rate_limit)
                log.warning(f"Rate limit reached. Waiting for {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class GeminiClient:
    """Client for interacting with Google's Gemini API."""
    
    def __init__(self):
        """Initialize Gemini client."""
        if not settings.gemini_api_key:
            log.warning("GEMINI_API_KEY not set. Gemini integration will not work.")
            return
            
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.rate_limiter = AsyncRateLimiter(settings.gemini_rate_limit)
        
    async def generate_content(self, prompt: str) -> str:
        """
        Generate content using Gemini.
        
        Args:
            prompt: The prompt to generate content for
            
        Returns:
            Generated text content
        """
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not set")
            
        await self.rate_limiter.acquire()
        
        try:
            # Run blocking API call in thread pool
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.agent_temperature,
                    max_output_tokens=settings.agent_max_tokens,
                )
            )
            return response.text
        except Exception as e:
            log.error(f"Error generating content with Gemini: {e}")
            raise

    async def generate_chat_response(
        self, 
        message: str, 
        history: List[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a chat response maintaining context.
        
        Args:
            message: The user's message
            history: List of previous messages (role, parts)
            
        Returns:
            Generated response text
        """
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not set")
            
        await self.rate_limiter.acquire()
        
        try:
            # Convert history to Gemini format
            chat_history = []
            if history:
                for msg in history:
                    role = "user" if msg.get("role") == "user" else "model"
                    chat_history.append({
                        "role": role,
                        "parts": [msg.get("content", "")]
                    })
            
            chat = self.model.start_chat(history=chat_history)
            
            response = await asyncio.to_thread(
                chat.send_message,
                message,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.agent_temperature,
                    max_output_tokens=settings.agent_max_tokens,
                )
            )
            return response.text
        except Exception as e:
            log.error(f"Error generating chat response with Gemini: {e}")
            raise


# Global client instance
_gemini_client = None

def get_gemini_client() -> GeminiClient:
    """Get or create the global Gemini client instance."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
