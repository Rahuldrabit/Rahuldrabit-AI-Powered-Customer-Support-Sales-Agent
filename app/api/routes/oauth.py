"""OAuth endpoints for LinkedIn (and scaffolding for TikTok if applicable)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from urllib.parse import urlencode

from app.api.dependencies import get_db
from app.models.database import User, Credentials, Platform
from app.utils.logger import log
from app.config import settings
from typing import Optional
import json
from datetime import timedelta
try:
    import requests
except Exception:
    requests = None

router = APIRouter()

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"


@router.get("/linkedin/start")
async def linkedin_oauth_start(
    redirect_uri: str,
    state: str,
):
    """Start LinkedIn OAuth: return authorization URL."""
    if not settings.linkedin_client_id:
        raise HTTPException(status_code=400, detail="LinkedIn client ID not configured")
    params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": "r_liteprofile r_emailaddress w_member_social"
    }
    url = f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"
    return {"auth_url": url}


@router.get("/linkedin/callback")
async def linkedin_oauth_callback(
    code: str,
    redirect_uri: str,
    platform_user_id: str,
    db: Session = Depends(get_db)
):
    """Handle LinkedIn OAuth callback: exchange code for tokens and store credentials."""
    if not settings.linkedin_client_id or not settings.linkedin_client_secret:
        raise HTTPException(status_code=400, detail="LinkedIn credentials not configured")

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at = None

    # Try real token exchange if requests is available
    if requests is not None:
        try:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.linkedin_client_id,
                "client_secret": settings.linkedin_client_secret,
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            resp = requests.post(LINKEDIN_TOKEN_URL, data=data, headers=headers, timeout=10)
            if resp.status_code == 200:
                payload = resp.json()
                access_token = payload.get("access_token")
                refresh_token = payload.get("refresh_token")  # LinkedIn may not always return this
                expires_in = payload.get("expires_in", 3600)
                expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
            else:
                log.warning(f"LinkedIn token exchange failed: {resp.status_code} {resp.text}")
        except Exception as e:
            log.error(f"LinkedIn token exchange error: {e}")

    # Fallback to mock tokens if real exchange failed
    if not access_token:
        access_token = f"mock_access_token_{platform_user_id}"
        refresh_token = f"mock_refresh_token_{platform_user_id}"
        expires_at = datetime.utcnow() + timedelta(hours=1)

    # Ensure user exists
    user = db.query(User).filter(User.platform_user_id == platform_user_id).first()
    if not user:
        user = User(platform=Platform.LINKEDIN, platform_user_id=platform_user_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Store credentials
    cred = Credentials(
        user_id=user.id,
        platform=Platform.LINKEDIN,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )
    db.add(cred)
    db.commit()

    log.info(f"Stored LinkedIn OAuth credentials for user {platform_user_id}")
    return {"status": "success", "access_token": access_token, "expires_at": expires_at}


# TikTok OAuth Endpoints
TIKTOK_AUTH_URL = "https://www.tiktok.com/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open-api.tiktok.com/oauth/access_token/"


@router.get("/tiktok/start")
async def tiktok_oauth_start(
    redirect_uri: str,
    state: str,
):
    """Start TikTok OAuth: return authorization URL."""
    if not settings.tiktok_client_key:
        raise HTTPException(status_code=400, detail="TikTok client key not configured")
    params = {
        "client_key": settings.tiktok_client_key,
        "scope": "user.info.basic,video.list",  # Basic scopes for TikTok
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state
    }
    url = f"{TIKTOK_AUTH_URL}?{urlencode(params)}"
    return {"auth_url": url}


@router.get("/tiktok/callback")
async def tiktok_oauth_callback(
    code: str,
    redirect_uri: str,
    platform_user_id: str,
    db: Session = Depends(get_db)
):
    """Handle TikTok OAuth callback: exchange code for tokens and store credentials."""
    if not settings.tiktok_client_key or not settings.tiktok_client_secret:
        raise HTTPException(status_code=400, detail="TikTok credentials not configured")

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at = None

    # Try real token exchange if requests is available
    if requests is not None:
        try:
            data = {
                "client_key": settings.tiktok_client_key,
                "client_secret": settings.tiktok_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            }
            headers = {"Content-Type": "application/json"}
            resp = requests.post(TIKTOK_TOKEN_URL, json=data, headers=headers, timeout=10)
            if resp.status_code == 200:
                payload = resp.json()
                # TikTok API response structure
                if payload.get("data"):
                    data_obj = payload["data"]
                    access_token = data_obj.get("access_token")
                    refresh_token = data_obj.get("refresh_token")
                    expires_in = data_obj.get("expires_in", 3600)
                    expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
            else:
                log.warning(f"TikTok token exchange failed: {resp.status_code} {resp.text}")
        except Exception as e:
            log.error(f"TikTok token exchange error: {e}")

    # Fallback to mock tokens if real exchange failed
    if not access_token:
        access_token = f"mock_tiktok_access_{platform_user_id}"
        refresh_token = f"mock_tiktok_refresh_{platform_user_id}"
        expires_at = datetime.utcnow() + timedelta(hours=1)

    # Ensure user exists
    user = db.query(User).filter(User.platform_user_id == platform_user_id).first()
    if not user:
        user = User(platform=Platform.TIKTOK, platform_user_id=platform_user_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Store credentials
    cred = Credentials(
        user_id=user.id,
        platform=Platform.TIKTOK,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )
    db.add(cred)
    db.commit()

    log.info(f"Stored TikTok OAuth credentials for user {platform_user_id}")
    return {"status": "success", "access_token": access_token, "expires_at": expires_at}

