"""Application configuration management."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "AI Customer Support Agent"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/customer_agent_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM Configuration
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    llm_provider: str = "mock"  # Options: openai, anthropic, mock

    # Agent Configuration
    agent_max_tokens: int = 500
    agent_temperature: float = 0.7
    agent_timeout_seconds: int = 30

    # TikTok Integration
    tiktok_client_key: Optional[str] = None
    tiktok_client_secret: Optional[str] = None
    tiktok_webhook_secret: Optional[str] = None

    # LinkedIn Integration
    linkedin_client_id: Optional[str] = None
    linkedin_client_secret: Optional[str] = None

    # Rate Limiting
    tiktok_rate_limit: int = 60  # requests per minute
    linkedin_rate_limit: int = 100  # requests per minute

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
