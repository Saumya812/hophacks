"""
FindMyPal backend configuration.

Loads settings from environment variables / a local .env file.
Keep secrets out of source control — use backend/.env locally.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    """Application settings read from the environment."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


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

    # Apify crawlers (Reddit / Instagram / Facebook) — optional
    apify_token: str = ""
    apify_reddit_actor: str = "scrapeforge~reddit-scraper"
    apify_instagram_actor: str = "apify~instagram-scraper"
    apify_facebook_actor: str = "scraper_one~facebook-posts-search"

    # Optional sponsor / advanced integrations
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_model: str = "eleven_monolingual_v1"
    backboard_api_key: str = ""
    spacetimedb_uri: str = "http://127.0.0.1:3000"
    spacetimedb_database: str = "findmypal"
    spacetimedb_token: str = ""
    snowflake_account: str = ""

    # Comma-separated list of allowed frontend origins (Vite may use 5173 or 5174)
    cors_origins: str = (
        "http://localhost:5173,http://localhost:5174,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    # Mock authenticated user (no real auth in v1)
    mock_user_id: str = "00000000-0000-0000-0000-000000000001"
    mock_user_email: str = "mock@findmypal.local"

    # If true, use first X-Forwarded-For hop for Lookup rate limits (behind a real proxy)
    trust_proxy: bool = False

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse CORS_ORIGINS into a clean list of origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton for dependency injection."""
    return Settings()
