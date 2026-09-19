"""
Supabase client factory for FindMyPal.

All DB access goes through the official supabase-py client so we stay
compatible with Supabase Auth / RLS later without rewriting queries.
"""

from functools import lru_cache

from supabase import Client, create_client

from config import get_settings


@lru_cache
def get_supabase() -> Client:
    """
    Return a cached Supabase client.

    Uses the service_role key on the server so the API can insert
    persons and sightings without an end-user JWT (auth is mocked).
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)
