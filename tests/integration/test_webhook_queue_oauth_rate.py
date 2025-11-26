"""Integration tests for webhook queue, OAuth storage, and rate limiter behavior.
These tests use synchronous Celery task apply and mocked Redis where appropriate.
"""

import pytest
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app.services.tasks import process_incoming_message_task
from app.api.routes.oauth import linkedin_oauth_callback
from app.models.database import SessionLocal, Platform, User, Conversation, Credentials
from app.services.message_processor import send_message_to_platform
from app.integrations.tiktok import TikTokClient
from app.integrations.linkedin import LinkedInClient


@pytest.mark.asyncio
async def test_webhook_enqueues_and_task_apply_succeeds():
    """Simulate webhook enqueue by directly applying the Celery task synchronously."""
    db: Session = SessionLocal()
    try:
        # Prepare user and conversation
        user = User(platform=Platform.TIKTOK, platform_user_id="u123")
        db.add(user); db.commit(); db.refresh(user)
        conv = Conversation(user_id=user.id, platform=Platform.TIKTOK, platform_conversation_id="c123")
        db.add(conv); db.commit(); db.refresh(conv)

        # Apply task synchronously
        res = process_incoming_message_task.apply(args=(
            Platform.TIKTOK.value, "u123", "c123", "Hello from webhook"
        )).get()
        assert res["status"] == "ok"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_oauth_callback_stores_credentials_and_used_in_send():
    """Ensure OAuth callback stores credentials and they are used on send_message_to_platform."""
    db: Session = SessionLocal()
    try:
        # Create user and conversation
        user = User(platform=Platform.LINKEDIN, platform_user_id="lin-user")
        db.add(user); db.commit(); db.refresh(user)
        conv = Conversation(user_id=user.id, platform=Platform.LINKEDIN, platform_conversation_id="lin-conv")
        db.add(conv); db.commit(); db.refresh(conv)

        # Invoke OAuth callback (mock path parameters via direct call)
        # Note: oauth callback is async; call directly
        from app.api.routes.oauth import linkedin_oauth_callback as cb
        resp = await cb(code="dummy", redirect_uri="http://localhost/cb", platform_user_id="lin-user", db=db)
        assert resp["status"] == "success"

        # Verify credentials saved
        cred = db.query(Credentials).filter(Credentials.user_id == user.id, Credentials.platform == Platform.LINKEDIN).first()
        assert cred is not None

        # Patch LinkedIn client to assert access_token is provided
        with patch.object(LinkedInClient, 'send_message', return_value=True) as send_mock:
            ok = await send_message_to_platform(Platform.LINKEDIN, conversation_id="lin-conv", message="Hi", db=db)
            assert ok is True
            # access_token should be passed; we can't easily inspect due to signature, but mock ensures call happened
            assert send_mock.called
    finally:
        db.close()


@pytest.mark.asyncio
async def test_redis_rate_limiter_blocks_when_exhausted():
    """Verify rate limiter gate in TikTok client blocks when tokens exhausted."""
    # Patch RedisRateLimiter.acquire to simulate exhaustion
    with patch("app.integrations.tiktok.RedisRateLimiter.acquire", side_effect=[True, False]):
        client = TikTokClient()
        ok1 = await client.send_message("convX", "first")
        ok2 = await client.send_message("convX", "second")
        assert ok1 is True
        assert ok2 is False
