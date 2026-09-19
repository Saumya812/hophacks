"""
FindMyPal backend configuration.

Loads settings from environment variables / a local .env file.
Keep secrets out of source control — use backend/.env locally.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings read from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase (PostgreSQL) connection via the official client
    supabase_url: str = "https://YOUR_PROJECT.supabase.co"
    supabase_key: str = "YOUR_SUPABASE_SERVICE_ROLE_KEY"

    # Google Gemini — natural search + Smart Person Search extraction
    gemini_api_key: str = "YOUR_GEMINI_API_KEY"
    # Optional override; empty = auto-detect via ListModels
    gemini_model: str = ""

    # Face matching — AWS Rekognition (optional)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"

    # Smart Person Search / lookup scrapers (all optional — skipped if unset)
    serpapi_key: str = ""
    newsapi_key: str = ""
    youtube_api_key: str = ""
    rapidapi_key: str = ""
    twitter_rapidapi_host: str = "twitter-api45.p.rapidapi.com"

    # Comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Mock authenticated user (no real auth in v1)
    mock_user_id: str = "00000000-0000-0000-0000-000000000001"
    mock_user_email: str = "mock@findmypal.local"

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse CORS_ORIGINS into a clean list of origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton for dependency injection."""
    return Settings()
