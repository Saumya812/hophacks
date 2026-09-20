"""Supabase database client used by the FastAPI application."""

from functools import lru_cache

from supabase import Client, create_client

from config import get_settings


class DatabaseError(RuntimeError):
    """Database error exposed as a safe API response by FastAPI."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


@lru_cache
def get_database() -> Client:
    """Return the cached server-side Supabase client."""

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise DatabaseError("Supabase is not configured.")
    try:
        return create_client(settings.supabase_url, settings.supabase_key)
    except Exception as exc:
        raise DatabaseError("Supabase configuration is invalid.") from exc


# Backwards-compatible name used by a few service modules.
get_supabase = get_database
