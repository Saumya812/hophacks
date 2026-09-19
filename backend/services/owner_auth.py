"""Owner tokens for family-only case mutations (hackathon-grade, not JWT)."""

from __future__ import annotations

import secrets
from typing import Dict, Optional
from uuid import UUID

from fastapi import HTTPException

from database import get_database

# Survives as long as the process; also persisted on persons.owner_token when 004 ran
_TOKENS: Dict[str, str] = {}


def issue_owner_token() -> str:
    return secrets.token_urlsafe(18)


def remember_token(person_id: str, token: str) -> None:
    if token:
        _TOKENS[str(person_id)] = token


def _stored_token(person_id: str) -> Optional[str]:
    rows = get_database().table("persons").select("owner_token").eq("id", str(person_id)).limit(1).execute().data
    return rows[0].get("owner_token") if rows else None


def require_owner(person_id: UUID, x_owner_token: Optional[str] = None) -> None:
    """
    Require X-Owner-Token for family actions on cases that have a token.
    Legacy rows with no token stay editable (pre-migration cases).
    """
    expected = _stored_token(str(person_id))
    if not expected:
        return
    got = (x_owner_token or "").strip()
    if not got or not secrets.compare_digest(got, expected):
        raise HTTPException(
            status_code=403,
            detail="This action requires the case owner token saved when the profile was created.",
        )
