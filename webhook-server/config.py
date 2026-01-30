"""Configuration settings loaded from environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Anthropic API
    anthropic_api_key: str

    # GitHub Configuration
    github_token: str
    github_webhook_secret: str

    # Smee.io Webhook Proxy
    smee_url: str

    # MongoDB Configuration
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "ai_review"

    # Server Configuration
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    # Review Configuration
    default_review_level: str = "auto"  # light, deep, auto


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()