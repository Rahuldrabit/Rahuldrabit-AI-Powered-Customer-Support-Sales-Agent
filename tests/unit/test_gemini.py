"""Tests for Gemini integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.integrations.gemini import GeminiClient, AsyncRateLimiter
from app.config import settings

@pytest.mark.asyncio
async def test_rate_limiter():
    """Test async rate limiter."""
    # Allow 2 requests per second
    limiter = AsyncRateLimiter(rate_limit=2, time_window=1)
    
    # First 2 should be immediate
    await limiter.acquire()
    await limiter.acquire()
    
    # Third should wait (we can't easily test the wait time without mocking time, 
    # but we can verify it doesn't block indefinitely)
    assert limiter.tokens == 0

@pytest.mark.asyncio
async def test_gemini_client_initialization():
    """Test Gemini client initialization."""
    with patch("app.integrations.gemini.genai") as mock_genai:
        # Mock settings
        settings.gemini_api_key = "test_key"
        
        client = GeminiClient()
        
        mock_genai.configure.assert_called_with(api_key="test_key")
        assert client.model is not None

@pytest.mark.asyncio
async def test_gemini_generate_content():
    """Test content generation."""
    with patch("app.integrations.gemini.genai") as mock_genai:
        settings.gemini_api_key = "test_key"
        
        # Mock model response
        mock_response = MagicMock()
        mock_response.text = "Generated content"
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        
        mock_genai.GenerativeModel.return_value = mock_model
        
        client = GeminiClient()
        response = await client.generate_content("Test prompt")
        
        assert response == "Generated content"
        mock_model.generate_content.assert_called_once()

@pytest.mark.asyncio
async def test_gemini_chat_response():
    """Test chat response generation."""
    with patch("app.integrations.gemini.genai") as mock_genai:
        settings.gemini_api_key = "test_key"
        
        # Mock chat response
        mock_response = MagicMock()
        mock_response.text = "Chat response"
        
        mock_chat = MagicMock()
        mock_chat.send_message.return_value = mock_response
        
        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat
        
        mock_genai.GenerativeModel.return_value = mock_model
        
        client = GeminiClient()
        response = await client.generate_chat_response("Hello", [{"role": "user", "content": "Hi"}])
        
        assert response == "Chat response"
        mock_model.start_chat.assert_called_once()
        mock_chat.send_message.assert_called_once()
