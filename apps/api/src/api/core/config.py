"""
Core configuration for the API.

"""
from functools import lru_cache

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


# Settings for the API
class APISettings (BaseSettings):
    """API settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    environment: str = "local"
    app_name: str = "Site Audit Platform API"

    # DB
    database_url: PostgresDsn

    #JWT
    jwt_secret: str
    jwt_algo: str = "HS256"

    #AWS
    aws_region: str = "us-east-2"

    # Anthropic (Claude)
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # Auditor
    audit_request_timeout_seconds: float = 20.0
    audit_user_agent: str = "SiteAuditBot/1.0 (+https://audit.foundryframe.com)"

    # Lighthouse (Google PageSpeed Insights API)
    pagespeed_api_key: str | None = None
    lighthouse_strategy: str = "mobile"
    lighthouse_timeout_seconds: float = 60.0

    #CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

@lru_cache
def get_api_settings() -> APISettings:
    """Get API settings."""
    return APISettings() # type: ignore[call-arg]