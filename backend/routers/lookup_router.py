"""
Smart Person Search — FastAPI routes.

POST /lookup/search
GET  /lookup/report/{report_id}
GET  /lookup/report/{report_id}/pdf

Includes:
- In-memory report cache (1 hour, keyed by normalized name)
- IP rate limit: 5 searches / hour
- Photos kept only in the ephemeral cache (never written to disk)
"""

from __future__ import annotations

import asyncio
import re
import time
import uuid
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from services.gemini_processor import (
    build_summary,
    extract_sightings_with_gemini,
    geocode_mentions,
    sort_sightings_chronologically,
)
from services.lookup_pdf import build_lookup_pdf
from services.scraper_service import collect_raw_mentions

router = APIRouter(prefix="/lookup", tags=["lookup"])

# ---------------------------------------------------------------------------
# In-memory cache + rate limiter (process-local; fine for single-instance demos)
# ---------------------------------------------------------------------------

CACHE_TTL_SECONDS = 60 * 60  # 1 hour
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 60 * 60

# name_key -> (expires_at, report_dict)
_name_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
# report_id -> (expires_at, report_dict)
_id_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
# ip -> deque of request timestamps
_rate_hits: Dict[str, Deque[float]] = defaultdict(deque)


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _purge_expired() -> None:
    now = time.time()
    for store in (_name_cache, _id_cache):
        dead = [k for k, (exp, _) in store.items() if exp <= now]
        for k in dead:
            del store[k]


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    hits = _rate_hits[ip]
    while hits and hits[0] <= now - RATE_LIMIT_WINDOW:
        hits.popleft()
    if len(hits) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded: max 5 Smart Person searches per hour from this IP.",
        )
    hits.append(now)


class LookupSearchRequest(BaseModel):
    """POST /lookup/search body."""

    name: str = Field(..., min_length=2, max_length=120, examples=["Jane Doe"])
    # Optional first/last for clients that send split fields — merged if name blank
    first_name: Optional[str] = Field(None, max_length=60)
    last_name: Optional[str] = Field(None, max_length=60)
    # data URL or raw base64 — never persisted to disk
    photo: Optional[str] = Field(
        None,
        description="Base64 photo or data URL (session-only, not stored permanently)",
    )


def _resolve_name(payload: LookupSearchRequest) -> str:
    if payload.name and payload.name.strip():
        return " ".join(payload.name.split())
    parts = [payload.first_name or "", payload.last_name or ""]
    joined = " ".join(p.strip() for p in parts if p and p.strip())
    if len(joined) < 2:
        raise HTTPException(status_code=422, detail="Provide a full name (first + last).")
    return joined


def _normalize_photo(photo: Optional[str]) -> Optional[str]:
    """Keep photo as a data URL in memory only; drop huge payloads."""
    if not photo:
        return None
    raw = photo.strip()
    # Cap ~2.5MB base64 to protect memory
    if len(raw) > 3_500_000:
        raise HTTPException(status_code=413, detail="Photo too large (max ~2.5MB).")
    if raw.startswith("data:image"):
        return raw
    # Assume raw base64 JPEG/PNG
    return f"data:image/jpeg;base64,{raw}"


async def _build_report(full_name: str, photo_data_url: Optional[str]) -> Dict[str, Any]:
    """Full pipeline: scrape → Gemini → geocode → summary."""
    scraped = await collect_raw_mentions(full_name)
    raw_mentions = scraped.get("raw_mentions") or []

    # Gemini call is sync (google-generativeai) — run in a thread
    sightings = await asyncio.to_thread(
        extract_sightings_with_gemini,
        full_name,
        raw_mentions,
    )
    sightings = sort_sightings_chronologically(sightings)
    locations = await geocode_mentions(sightings)
    summary = build_summary(full_name, photo_data_url, sightings, locations)

    report_id = str(uuid.uuid4())
    report = {
        "report_id": report_id,
        "summary": summary,
        "sightings": sightings,
        "locations": locations,
        "raw_mentions": [
            {
                "source": m.get("source"),
                "date": m.get("date"),
                "title": m.get("title"),
                "snippet": m.get("snippet") or m.get("text"),
                "url": m.get("url"),
            }
            for m in raw_mentions
        ],
        "sources_status": scraped.get("sources_status") or {},
        "empty": len(sightings) == 0 and len(raw_mentions) == 0,
    }
    return report


@router.post("/search", summary="Run Smart Person Search")
async def lookup_search(payload: LookupSearchRequest, request: Request) -> Dict[str, Any]:
    """
    Scrape public sources in parallel, extract sightings with Gemini,
    geocode locations, and return a structured report.
    """
    _purge_expired()
    ip = _client_ip(request)
    _check_rate_limit(ip)

    full_name = _resolve_name(payload)
    name_key = _normalize_name(full_name)
    photo_data_url = _normalize_photo(payload.photo)

    # Cache hit by name — only reuse if we previously extracted structured mentions
    cached = _name_cache.get(name_key)
    if cached and cached[0] > time.time() and (cached[1].get("sightings") or []):
        report = dict(cached[1])
        if photo_data_url and report.get("summary"):
            report = {
                **report,
                "summary": {**report["summary"], "photo_data_url": photo_data_url},
            }
            _id_cache[report["report_id"]] = (cached[0], report)
        report["cached"] = True
        return report

    report = await _build_report(full_name, photo_data_url)
    report["cached"] = False

    # Do not cache empty/sparse reports — lets improved extractors retry
    if report.get("empty") or (
        not (report.get("sightings") or []) and (report.get("raw_mentions") or [])
    ):
        # Still keep by id briefly so PDF works for this session
        _id_cache[report["report_id"]] = (time.time() + CACHE_TTL_SECONDS, report)
        return report

    expires = time.time() + CACHE_TTL_SECONDS
    _name_cache[name_key] = (expires, report)
    _id_cache[report["report_id"]] = (expires, report)
    return report


@router.get("/report/{report_id}", summary="Fetch a cached lookup report")
async def get_lookup_report(report_id: str) -> Dict[str, Any]:
    _purge_expired()
    entry = _id_cache.get(report_id)
    if not entry or entry[0] <= time.time():
        raise HTTPException(status_code=404, detail="Report not found or expired (1-hour cache).")
    return entry[1]


@router.get("/report/{report_id}/pdf", summary="Download lookup report as PDF")
async def get_lookup_report_pdf(report_id: str) -> Response:
    _purge_expired()
    entry = _id_cache.get(report_id)
    if not entry or entry[0] <= time.time():
        raise HTTPException(status_code=404, detail="Report not found or expired (1-hour cache).")

    pdf_bytes = await asyncio.to_thread(build_lookup_pdf, entry[1])
    filename = f"FindMyPal_Lookup_{report_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
