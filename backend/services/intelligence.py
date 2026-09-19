"""
AI intelligence helpers: case summarizer, duplicate detection, tip credibility.
"""

from __future__ import annotations

import json
import logging
import math
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from database import get_database
from services.face_match import compare_faces, _download_image, _decode_photo
from services.gemini_client import gemini_configured, get_generative_model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AI Case Summarizer
# ---------------------------------------------------------------------------

def generate_case_summary(person_id: str, *, persist: bool = False, refresh: bool = False) -> Dict[str, Any]:
    """
    Build a one-paragraph plain-English summary from person + sightings.
    GET uses stored/heuristic text (no Gemini, no write).
    POST refresh generates (Gemini if available) and persists.
    """
    try:
        database = get_database()
        person_res = database.table("persons").select("*").eq("id", person_id).limit(1).execute()
        if not person_res.data:
            return {
                "person_id": person_id,
                "summary": "Case profile could not be loaded for summary.",
                "engine": "error",
                "sighting_count": 0,
                "persisted": False,
                "generated_at": datetime.utcnow().isoformat() + "Z",
            }
        person = person_res.data[0]
        if not refresh and person.get("ai_summary"):
            return {
                "person_id": person_id,
                "summary": person["ai_summary"],
                "engine": "stored",
                "sighting_count": 0,
                "persisted": True,
                "generated_at": person.get("ai_summary_updated_at")
                or datetime.utcnow().isoformat() + "Z",
            }

        try:
            sight_res = (
                database.table("sightings")
                .select("*")
                .eq("person_id", person_id)
                .order("date_time", desc=False)
                .execute()
            )
            sightings = sight_res.data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sightings fetch for summary failed: %s", exc)
            sightings = []

        if not gemini_configured() or not refresh:
            summary = _heuristic_summary(person, sightings)
            engine = "heuristic"
        else:
            try:
                summary = _gemini_summary(person, sightings)
                engine = "gemini"
            except Exception as exc:  # noqa: BLE001
                logger.warning("Gemini summary failed: %s", exc)
                summary = _heuristic_summary(person, sightings)
                engine = "heuristic_fallback"

        persisted = False
        if persist:
            try:
                database.table("persons").update(
                    {
                        "ai_summary": summary,
                        "ai_summary_updated_at": datetime.utcnow().isoformat() + "Z",
                    }
                ).eq("id", person_id).execute()
                persisted = True
            except Exception:  # noqa: BLE001
                persisted = False

        return {
            "person_id": person_id,
            "summary": summary,
            "engine": engine,
            "sighting_count": len(sightings),
            "persisted": persisted,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("generate_case_summary failed: %s", exc)
        return {
            "person_id": person_id,
            "summary": "Summary is temporarily unavailable. Try Refresh in a moment.",
            "engine": "error",
            "sighting_count": 0,
            "persisted": False,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }


def _heuristic_summary(person: Dict[str, Any], sightings: List[Dict[str, Any]]) -> str:
    name = person.get("name") or "This person"
    loc = person.get("last_seen_location") or "an unknown location"
    date = person.get("last_seen_date") or "an unknown date"
    n = len(sightings)
    if n == 0:
        return (
            f"{name} was reported missing near {loc} (last seen {date}). "
            f"No public tip sightings have been submitted yet."
        )
    latest = sightings[-1]
    tip_loc = f"{latest.get('location_lat')}, {latest.get('location_lng')}"
    return (
        f"Based on {n} report{'s' if n != 1 else ''}, {name} was last officially noted near {loc} "
        f"on {date}. The most recent tip points near coordinates {tip_loc}: "
        f"\"{(latest.get('description') or '')[:160]}\"."
    )


def _gemini_summary(person: Dict[str, Any], sightings: List[Dict[str, Any]]) -> str:
    model = get_generative_model(
        system_instruction=(
            "You write one plain-English paragraph summarizing a missing-person case "
            "for families. Use only provided facts. Do not invent locations or certainty. "
            "Separate confirmed profile fields from unreviewed tips. Max 80 words."
        )
    )
    payload = {
        "profile": {
            "name": person.get("name"),
            "age": person.get("age"),
            "last_seen_location": person.get("last_seen_location"),
            "last_seen_date": person.get("last_seen_date"),
            "description": person.get("description"),
            "status": person.get("status"),
        },
        "tips": [
            {
                "id": s.get("id"),
                "date_time": s.get("date_time"),
                "lat": s.get("location_lat"),
                "lng": s.get("location_lng"),
                "description": s.get("description"),
                "confidence_level": s.get("confidence_level"),
                "credibility_score": s.get("credibility_score"),
            }
            for s in sightings[:40]
        ],
    }
    resp = model.generate_content(
        f"Summarize this case:\n{json.dumps(payload, ensure_ascii=False)}",
        generation_config={"temperature": 0.2},
    )
    text = (getattr(resp, "text", None) or "").strip()
    if not text:
        raise ValueError("Empty Gemini summary")
    return text


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def _name_similarity(a: str, b: str) -> float:
    """Token Jaccard + sequence ratio hybrid, 0–100."""
    from difflib import SequenceMatcher

    a_n = re.sub(r"[^a-z0-9 ]", "", (a or "").lower()).strip()
    b_n = re.sub(r"[^a-z0-9 ]", "", (b or "").lower()).strip()
    if not a_n or not b_n:
        return 0.0
    seq = SequenceMatcher(None, a_n, b_n).ratio() * 100
    ta, tb = set(a_n.split()), set(b_n.split())
    jacc = (len(ta & tb) / len(ta | tb) * 100) if (ta | tb) else 0.0
    return max(seq, jacc)


def find_duplicate_candidates(
    *,
    name: str,
    photo_b64: Optional[str] = None,
    photo_url: Optional[str] = None,
    age: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Check whether a similar active/found case already exists.
    Combines name similarity with optional photo matching.
    """
    database = get_database()
    rows = (
        database.table("persons")
        .select("*")
        .in_("status", ["active", "found"])
        .execute()
        .data
        or []
    )

    probe_bytes = None
    if photo_b64:
        try:
            probe_bytes = _decode_photo(photo_b64)
        except Exception:  # noqa: BLE001
            probe_bytes = None
    elif photo_url:
        probe_bytes = _download_image(photo_url)

    candidates: List[Dict[str, Any]] = []
    for row in rows:
        name_score = _name_similarity(name, row.get("name") or "")
        age_bonus = 0.0
        if age is not None and row.get("age") is not None:
            diff = abs(int(age) - int(row["age"]))
            if diff == 0:
                age_bonus = 10
            elif diff <= 2:
                age_bonus = 5

        photo_score = None
        if probe_bytes and row.get("photo_url"):
            cand = _download_image(row["photo_url"])
            if cand:
                try:
                    photo_score, _eng = compare_faces(probe_bytes, cand)
                except Exception:  # noqa: BLE001
                    photo_score = None

        # Combined score
        if photo_score is not None:
            combined = 0.45 * name_score + 0.45 * photo_score + 0.1 * (age_bonus * 10)
        else:
            combined = 0.85 * name_score + 0.15 * (age_bonus * 10)

        if combined >= 55 or name_score >= 80 or (photo_score or 0) >= 70:
            candidates.append(
                {
                    "person_id": row["id"],
                    "name": row.get("name"),
                    "age": row.get("age"),
                    "status": row.get("status"),
                    "photo_url": row.get("photo_url"),
                    "last_seen_location": row.get("last_seen_location"),
                    "name_similarity": round(name_score, 1),
                    "photo_similarity": round(photo_score, 1) if photo_score is not None else None,
                    "combined_score": round(min(combined, 100), 1),
                }
            )

    candidates.sort(key=lambda c: c["combined_score"], reverse=True)
    return {
        "possible_duplicate": len(candidates) > 0,
        "message": (
            f"Possible duplicate: {len(candidates)} similar case(s) already exist"
            if candidates
            else "No similar cases detected"
        ),
        "candidates": candidates[:5],
    }


# ---------------------------------------------------------------------------
# Sighting credibility scorer (1–10)
# ---------------------------------------------------------------------------

def score_sighting_credibility(
    *,
    description: str,
    location_lat: float,
    location_lng: float,
    date_time: Any,
    person_id: str,
) -> Dict[str, Any]:
    """
    Score a tip 1–10 from specificity, time language, detail length,
    and geographic agreement with other tips.
    """
    desc = (description or "").strip()
    reasons: List[str] = []
    score = 3.0  # baseline

    # Length / detail
    words = len(desc.split())
    if words >= 40:
        score += 2
        reasons.append("Detailed description")
    elif words >= 15:
        score += 1
        reasons.append("Moderate detail")
    else:
        reasons.append("Short description")

    # Time reference in text or structured date_time
    time_pat = re.compile(
        r"\b(\d{1,2}:\d{2}|am|pm|morning|afternoon|evening|night|yesterday|"
        r"today|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
        r"january|february|march|april|may|june|july|august|september|"
        r"october|november|december|\d{1,2}/\d{1,2}/\d{2,4})\b",
        re.I,
    )
    if date_time:
        score += 1.5
        reasons.append("Structured date/time provided")
    if time_pat.search(desc):
        score += 1
        reasons.append("Time language in description")

    # Location specificity in text
    loc_pat = re.compile(
        r"\b(street|st\.|ave|road|rd\.|boulevard|near|corner|station|campus|"
        r"hospital|park|mall|harbor|downtown|intersection)\b",
        re.I,
    )
    if loc_pat.search(desc):
        score += 1.5
        reasons.append("Specific location cues")

    # Geographic clustering with existing tips
    try:
        existing = (
            get_database()
            .table("sightings")
            .select("location_lat,location_lng")
            .eq("person_id", person_id)
            .execute()
            .data
            or []
        )
        nearby = 0
        for s in existing:
            dkm = _haversine_km(
                location_lat,
                location_lng,
                float(s["location_lat"]),
                float(s["location_lng"]),
            )
            if dkm <= 1.5:
                nearby += 1
        if nearby >= 2:
            score += 2
            reasons.append(f"Agrees with {nearby} nearby tips (≤1.5km)")
        elif nearby == 1:
            score += 1
            reasons.append("Near one prior tip")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Geo credibility check failed: %s", exc)

    score = max(1, min(10, int(round(score))))
    family_flag = score >= 7
    if family_flag:
        reasons.append("Flagged for family review")

    return {
        "credibility_score": score,
        "family_review_flag": family_flag,
        "reasons": reasons,
    }


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
