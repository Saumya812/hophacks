"""
Backboard-style persistent search memory.

Uses local `search_memory` table when Backboard credentials are absent.
Never claims live Backboard unless BACKBOARD_API_KEY is configured.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, Optional

from config import get_settings
from database import get_supabase
from services.advanced import utcnow

logger = logging.getLogger(__name__)


def backboard_configured() -> bool:
    key = get_settings().backboard_api_key or ""
    return bool(key) and not key.upper().startswith("YOUR_")


def remember_search(
    participant_key: str,
    *,
    city: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    filters: Optional[dict] = None,
) -> Dict[str, Any]:
    payload = {
        "participant_key": participant_key,
        "city": city,
        "date_from": date_from,
        "date_to": date_to,
        "filters_json": filters or {},
        "updated_at": utcnow().isoformat(),
    }
    # Prefer local mapping always for isolation; Backboard remote sync is optional future work
    try:
        sb = get_supabase()
        existing = (
            sb.table("search_memory")
            .select("id")
            .eq("participant_key", participant_key)
            .limit(1)
            .execute()
            .data
        )
        if existing:
            sb.table("search_memory").update(payload).eq("participant_key", participant_key).execute()
        else:
            sb.table("search_memory").insert(payload).execute()
        return {
            "ok": True,
            "provider": "backboard" if backboard_configured() else "local_search_memory",
            "backboard_live": backboard_configured(),
            "memory": payload,
            "note": (
                "Stored in local search_memory table. "
                + ("Backboard key present but remote sync not enabled in this build." if backboard_configured() else "Backboard unavailable — local stand-in only.")
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "provider": "unavailable"}


def recall_search(participant_key: str) -> Dict[str, Any]:
    try:
        rows = (
            get_supabase()
            .table("search_memory")
            .select("*")
            .eq("participant_key", participant_key)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            return {"found": False, "provider": "local_search_memory", "backboard_live": False}
        return {
            "found": True,
            "provider": "local_search_memory",
            "backboard_live": backboard_configured(),
            "memory": rows[0],
        }
    except Exception as exc:  # noqa: BLE001
        return {"found": False, "error": str(exc), "provider": "unavailable"}


def forget_search(participant_key: str) -> Dict[str, Any]:
    try:
        get_supabase().table("search_memory").delete().eq("participant_key", participant_key).execute()
        return {
            "ok": True,
            "forgotten": True,
            "provider": "local_search_memory",
            "note": "Local mapping deleted. Remote Backboard delete not invoked in this build.",
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
