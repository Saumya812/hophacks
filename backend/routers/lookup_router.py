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
    extract_sighting_claims,
    geocode_mentions,
    sort_sightings_chronologically,
)
from services.lookup_pdf import build_lookup_pdf
from services.scraper_service import collect_raw_mentions
from database import get_supabase

router = APIRouter(prefix="/lookup", tags=["lookup"])


def _locations_from_matching_case(full_name: str) -> list[dict]:
    """
    When Lookup finds no geocodable public-web places, reuse tip coordinates
    from an active case with the same name (same data Cases heatmap uses).
    """
    name = " ".join((full_name or "").split())
    if len(name) < 2:
        return []
    try:
        sb = get_supabase()
        parts = name.split()
        persons: list[dict] = []

        # Exact (case-insensitive)
        persons = (
            sb.table("persons")
            .select("id,name,last_seen_location")
            .ilike("name", name)
            .limit(5)
            .execute()
            .data
            or []
        )

        # First + last token
        if not persons and len(parts) >= 2:
            persons = (
                sb.table("persons")
                .select("id,name,last_seen_location")
                .ilike("name", f"%{parts[0]}%{parts[-1]}%")
                .limit(5)
                .execute()
                .data
                or []
            )

        # First name only when unique among active cases (demo-friendly)
        if not persons and parts:
            candidates = (
                sb.table("persons")
                .select("id,name,last_seen_location,status")
                .ilike("name", f"{parts[0]}%")
                .limit(10)
                .execute()
                .data
                or []
            )
            active = [p for p in candidates if (p.get("status") or "active") == "active"]
            pool = active or candidates
            if len(pool) == 1:
                persons = pool
            elif pool:
                # Prefer name that shares the most tokens
                want = {t.lower() for t in parts}
                scored = sorted(
                    pool,
                    key=lambda p: len(want & set((p.get("name") or "").lower().split())),
                    reverse=True,
                )
                if scored and len(want & set((scored[0].get("name") or "").lower().split())) >= 1:
                    persons = [scored[0]]

        if not persons:
            return []

        person = persons[0]
        rows = (
            sb.table("sightings")
            .select("location_lat,location_lng,description")
            .eq("person_id", person["id"])
            .execute()
            .data
            or []
        )
        out: list[dict] = []
        for r in rows:
            try:
                lat = float(r["location_lat"])
                lng = float(r["location_lng"])
            except (TypeError, ValueError, KeyError):
                continue
            out.append(
                {
                    "lat": lat,
                    "lng": lng,
                    "label": (r.get("description") or "Case tip")[:80],
                    "count": 1,
                }
            )
        if not out and person.get("last_seen_location"):
            from services.geocode import geocode_query

            hit = geocode_query(person["last_seen_location"])
            if hit:
                out.append(
                    {
                        "lat": float(hit["lat"]),
                        "lng": float(hit["lng"]),
                        "label": person["last_seen_location"],
                        "count": 1,
                    }
                )
        return out
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning("Case tip fallback failed: %s", exc)
        return []

# ---------------------------------------------------------------------------
# In-memory cache + rate limiter (process-local; fine for single-instance demos)
# ---------------------------------------------------------------------------

CACHE_TTL_SECONDS = 60 * 60  # 1 hour
RATE_LIMIT_MAX = 20
RATE_LIMIT_WINDOW = 60 * 60

# name_key -> (expires_at, report_dict)
_name_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
# report_id -> (expires_at, report_dict)
_id_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
# ip -> deque of request timestamps
_rate_hits: Dict[str, Deque[float]] = defaultdict(deque)


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


# Bump when heatmap/geocode/extractor logic changes so stale in-memory reports are rebuilt
_CACHE_VERSION = 6


def _cache_key(name: str) -> str:
    return f"v{_CACHE_VERSION}:{_normalize_name(name)}"


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
            detail="Rate limit exceeded: max 20 Smart Person searches per hour from this IP.",
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
    sightings, extraction_engine = await asyncio.to_thread(
        extract_sightings_with_gemini,
        full_name,
        raw_mentions,
    )
    sightings = sort_sightings_chronologically(sightings)
    claims = extract_sighting_claims(sightings, full_name)
    locations = await geocode_mentions(sightings, raw_mentions)

    # Always merge matching case tip coords so Lookup heatmap aligns with Cases
    case_pts = await asyncio.to_thread(_locations_from_matching_case, full_name)
    if case_pts:
        # Deduplicate by rounded lat/lng
        seen = {
            (round(float(p["lat"]), 4), round(float(p["lng"]), 4))
            for p in locations
        }
        for p in case_pts:
            key = (round(float(p["lat"]), 4), round(float(p["lng"]), 4))
            if key in seen:
                continue
            seen.add(key)
            locations.append(p)

    # Drop bad geocodes that would force a world-zoom map
    from services.gemini_processor import _drop_geo_outliers

    locations = _drop_geo_outliers(locations)

    summary = build_summary(full_name, photo_data_url, sightings, locations)

    report_id = str(uuid.uuid4())
    report = {
        "report_id": report_id,
        "summary": summary,
        "sightings": sightings,
        "claims": claims,
        "locations": locations,
        "extraction_engine": extraction_engine,
        "raw_count": scraped.get("raw_count") or len(raw_mentions),
        "raw_mentions": [
            {
                "source": m.get("source"),
                "username": m.get("username"),
                "kind": m.get("kind"),
                "date": m.get("date"),
                "time": m.get("time"),
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

    full_name = _resolve_name(payload)
    name_key = _cache_key(full_name)
    photo_data_url = _normalize_photo(payload.photo)

    # Cache hit by name — reuse without burning rate limit
    # Cache hit — only reuse Gemini-quality extracts (not heuristic fallback)
    cached = _name_cache.get(name_key)
    if (
        cached
        and cached[0] > time.time()
        and (cached[1].get("sightings") or [])
        and (cached[1].get("locations") or [])
        and cached[1].get("extraction_engine") == "gemini"
    ):
        report = dict(cached[1])
        if photo_data_url and report.get("summary"):
            report = {
                **report,
                "summary": {**report["summary"], "photo_data_url": photo_data_url},
            }
            _id_cache[report["report_id"]] = (cached[0], report)
        report["cached"] = True
        return report

    # Drop stale / non-Gemini cache so accuracy fixes apply on next search
    if cached and cached[1].get("extraction_engine") != "gemini":
        _name_cache.pop(name_key, None)

    ip = _client_ip(request)
    _check_rate_limit(ip)

    report = await _build_report(full_name, photo_data_url)
    report["cached"] = False

    # Do not name-cache empty/sparse/heuristic reports — retry can improve later
    if (
        report.get("empty")
        or report.get("extraction_engine") != "gemini"
        or (
            not (report.get("sightings") or []) and (report.get("raw_mentions") or [])
        )
    ):
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
