"""
Advanced feature routes: alerts, live feed, clusters, engagement, found flow,
coordinators, social kit data, dashboard, patterns, audio, search memory.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field

from database import get_supabase
from services.advanced import (
    activity_buckets,
    city_dashboard_stats,
    cross_case_patterns,
    get_live_tips,
    queue_email,
    recompute_tips_count,
    utcnow,
)
from services.backboard_memory import forget_search, recall_search, remember_search
from services.elevenlabs_tts import CACHE_DIR, synthesize_speech
from pathlib import Path

router = APIRouter(tags=["advanced"])


# -------------------- models --------------------

class NLAlertCreate(BaseModel):
    email: EmailStr
    query_text: str = Field(..., min_length=8, max_length=500)


class ZipAlertCreate(BaseModel):
    email: EmailStr
    zip_code: str = Field(..., min_length=3, max_length=12)


class CaseWatchCreate(BaseModel):
    email: EmailStr
    person_id: UUID


class CaseUpdateCreate(BaseModel):
    body: str = Field(..., min_length=3, max_length=4000)
    author_email: Optional[EmailStr] = None


class CoordinatorInvite(BaseModel):
    email: EmailStr
    role: str = "coordinator"


class FoundPayload(BaseModel):
    message: Optional[str] = Field(None, max_length=1000)


class FlagPayload(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class VerifyPayload(BaseModel):
    police_report_number: str = Field(..., min_length=2, max_length=100)


class MemoryRemember(BaseModel):
    participant_key: str = Field(..., min_length=3, max_length=120)
    city: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    filters: Optional[dict] = None


class AudioRequest(BaseModel):
    text: Optional[str] = None  # if omitted, build from public profile fields


# -------------------- live feed / analytics --------------------

@router.get("/live/tips")
def live_tips(limit: int = Query(10, ge=1, le=50)):
    """Homepage live tip feed (polling stand-in for SpacetimeDB)."""
    tips = get_live_tips(limit)
    return {
        "tips": tips,
        "transport": "polling",
        "spacetime": "unavailable",
        "note": "Clients should poll every few seconds. SpacetimeDB not configured — this is a visibly identified fallback.",
    }


@router.get("/dashboard/city")
def dashboard_city():
    return city_dashboard_stats()


@router.get("/analytics/case-activity/{person_id}")
def case_activity(person_id: UUID, bucket_hours: int = Query(24, ge=1, le=168)):
    return activity_buckets(str(person_id), bucket_hours=bucket_hours)


@router.get("/analytics/cross-case-patterns")
def patterns(radius_km: float = Query(2.0, ge=0.5, le=50)):
    return cross_case_patterns(radius_km=radius_km)


@router.get("/analytics/platform-mentions/{person_id}")
def platform_mentions(person_id: UUID):
    """
    Donut-chart data. Uses tip credibility reasons / description heuristics
    plus optional lookup raw mentions if none — here we classify tip text lightly.
    """
    rows = (
        get_supabase()
        .table("sightings")
        .select("description")
        .eq("person_id", str(person_id))
        .execute()
        .data
        or []
    )
    counts = {"community_tips": len(rows), "reddit": 0, "news": 0, "x": 0, "other": 0}
    for r in rows:
        t = (r.get("description") or "").lower()
        if "reddit" in t:
            counts["reddit"] += 1
        elif "news" in t or "article" in t:
            counts["news"] += 1
        elif "twitter" in t or " tweet" in t or " on x " in t:
            counts["x"] += 1
        else:
            counts["other"] += 1
    total = max(sum(counts.values()), 1)
    slices = [
        {"platform": k, "count": v, "pct": round(100 * v / total, 1)}
        for k, v in counts.items()
        if v > 0
    ]
    return {"person_id": str(person_id), "slices": slices, "total": total}


# -------------------- alerts --------------------

@router.post("/alerts/natural")
def create_nl_alert(payload: NLAlertCreate):
    row = {
        "kind": "natural_language",
        "email": str(payload.email),
        "query_text": payload.query_text,
        "active": True,
    }
    try:
        res = get_supabase().table("alert_subscriptions").insert(row).execute()
        return {"ok": True, "alert": (res.data or [row])[0]}
    except Exception as exc:
        raise HTTPException(503, f"Alerts table unavailable — run migration 003. ({exc})") from exc


@router.post("/alerts/zip")
def create_zip_alert(payload: ZipAlertCreate):
    row = {
        "kind": "zip",
        "email": str(payload.email),
        "zip_code": payload.zip_code,
        "active": True,
    }
    try:
        res = get_supabase().table("alert_subscriptions").insert(row).execute()
        return {"ok": True, "alert": (res.data or [row])[0]}
    except Exception as exc:
        raise HTTPException(503, f"Alerts table unavailable — run migration 003. ({exc})") from exc


@router.post("/alerts/watch")
def watch_case(payload: CaseWatchCreate):
    sb = get_supabase()
    row = {
        "kind": "case_watch",
        "email": str(payload.email),
        "person_id": str(payload.person_id),
        "active": True,
    }
    try:
        res = sb.table("alert_subscriptions").insert(row).execute()
        person = sb.table("persons").select("watchers_count").eq("id", str(payload.person_id)).limit(1).execute().data
        n = int((person or [{}])[0].get("watchers_count") or 0) + 1
        sb.table("persons").update({"watchers_count": n}).eq("id", str(payload.person_id)).execute()
        return {"ok": True, "alert": (res.data or [row])[0], "watchers_count": n}
    except Exception as exc:
        raise HTTPException(503, f"Watch unavailable — run migration 003. ({exc})") from exc


# -------------------- case management --------------------

@router.get("/persons/{person_id}/engagement")
def engagement(person_id: UUID):
    sb = get_supabase()
    p = sb.table("persons").select("*").eq("id", str(person_id)).limit(1).execute().data
    if not p:
        raise HTTPException(404, "Person not found")
    person = p[0]
    tips = recompute_tips_count(str(person_id))
    return {
        "person_id": str(person_id),
        "watchers": person.get("watchers_count") or 0,
        "tips_submitted": tips,
        "shares": person.get("shares_count") or 0,
        "label": f"{person.get('watchers_count') or 0} watching · {tips} tips · shared {person.get('shares_count') or 0} times",
    }


@router.post("/persons/{person_id}/share")
def record_share(person_id: UUID):
    sb = get_supabase()
    p = sb.table("persons").select("shares_count").eq("id", str(person_id)).limit(1).execute().data
    if not p:
        raise HTTPException(404, "Person not found")
    n = int(p[0].get("shares_count") or 0) + 1
    try:
        sb.table("persons").update({"shares_count": n}).eq("id", str(person_id)).execute()
    except Exception:
        pass
    return {"shares_count": n}


@router.get("/persons/{person_id}/social-kit")
def social_kit(person_id: UUID):
    sb = get_supabase()
    p = sb.table("persons").select("*").eq("id", str(person_id)).limit(1).execute().data
    if not p:
        raise HTTPException(404, "Person not found")
    person = p[0]
    name = person.get("name")
    loc = person.get("last_seen_location")
    desc = (person.get("description") or "")[:180]
    link = f"/person/{person_id}"
    tags = "#MissingPerson #FindMyPal #HaveYouSeenThem"
    return {
        "person_id": str(person_id),
        "posts": {
            "x": f"MISSING: {name}. Last seen near {loc}. {desc} Please share. {tags} {link}",
            "instagram": f"Please help us find {name}.\n\nLast seen: {loc}\n{desc}\n\n{tags}\n{link}",
            "facebook": f"We are searching for {name}, last seen near {loc}. {desc}\n\nIf you have information, submit a tip on FindMyPal.\n{link}\n\n{tags}",
            "tiktok": f"Have you seen {name}? Last seen {loc}. Full case on FindMyPal. {tags}",
        },
    }


@router.post("/persons/{person_id}/updates")
def add_case_update(person_id: UUID, payload: CaseUpdateCreate):
    sb = get_supabase()
    row = {
        "person_id": str(person_id),
        "body": payload.body,
        "author_email": str(payload.author_email) if payload.author_email else None,
    }
    try:
        res = sb.table("case_updates").insert(row).execute()
    except Exception as exc:
        raise HTTPException(503, f"case_updates missing — run migration 003 ({exc})") from exc

    # Broadcast to watchers
    watchers = (
        sb.table("alert_subscriptions")
        .select("email")
        .eq("person_id", str(person_id))
        .eq("active", True)
        .execute()
        .data
        or []
    )
    person = sb.table("persons").select("name").eq("id", str(person_id)).limit(1).execute().data
    name = (person or [{}])[0].get("name") or "a case"
    sent = []
    for w in watchers:
        if w.get("email"):
            sent.append(
                queue_email(
                    w["email"],
                    f"Update on {name}",
                    payload.body,
                    kind="case_update",
                    meta={"person_id": str(person_id)},
                )
            )
    return {"update": (res.data or [row])[0], "emails_logged": len(sent)}


@router.get("/persons/{person_id}/updates")
def list_updates(person_id: UUID):
    try:
        rows = (
            get_supabase()
            .table("case_updates")
            .select("*")
            .eq("person_id", str(person_id))
            .order("created_at", desc=True)
            .execute()
            .data
            or []
        )
        return {"count": len(rows), "updates": rows}
    except Exception:
        return {"count": 0, "updates": [], "note": "Run migration 003"}


@router.post("/persons/{person_id}/coordinators")
def invite_coordinator(person_id: UUID, payload: CoordinatorInvite):
    # Cap at 4 coordinators + implicit owner
    sb = get_supabase()
    existing = sb.table("case_coordinators").select("id").eq("person_id", str(person_id)).execute().data or []
    if len(existing) >= 4:
        raise HTTPException(400, "Maximum 4 coordinators per case")
    row = {"person_id": str(person_id), "email": str(payload.email), "role": payload.role}
    try:
        res = sb.table("case_coordinators").insert(row).execute()
    except Exception as exc:
        raise HTTPException(503, f"coordinators table missing — run migration 003 ({exc})") from exc
    queue_email(
        str(payload.email),
        "You were invited as a FindMyPal case coordinator",
        f"You can help approve tips, post updates, and generate flyers for case {person_id}.",
        kind="coordinator_invite",
    )
    return {"coordinator": (res.data or [row])[0]}


@router.get("/persons/{person_id}/coordinators")
def list_coordinators(person_id: UUID):
    try:
        rows = (
            get_supabase()
            .table("case_coordinators")
            .select("*")
            .eq("person_id", str(person_id))
            .execute()
            .data
            or []
        )
        return {"count": len(rows), "coordinators": rows}
    except Exception:
        return {"count": 0, "coordinators": []}


@router.post("/persons/{person_id}/found")
def mark_found(person_id: UUID, payload: FoundPayload):
    sb = get_supabase()
    update = {
        "status": "found",
        "found_at": utcnow().isoformat(),
        "found_message": payload.message or "Found safe",
    }
    res = sb.table("persons").update(update).eq("id", str(person_id)).execute()
    if not res.data:
        raise HTTPException(404, "Person not found")
    # Thank tip submitters (emails only if present — still logged server-side)
    tips = sb.table("sightings").select("submitter_email").eq("person_id", str(person_id)).execute().data or []
    thanked = set()
    for t in tips:
        em = t.get("submitter_email")
        if em and em not in thanked:
            thanked.add(em)
            queue_email(
                em,
                "Thank you — a FindMyPal case was marked found safe",
                "Thank you for submitting a tip. The family marked this case as found/resolved.",
                kind="found_thanks",
                meta={"person_id": str(person_id)},
            )
    return {"person": res.data[0], "thank_you_emails_logged": len(thanked)}


@router.post("/persons/{person_id}/verify-police")
def verify_police(person_id: UUID, payload: VerifyPayload):
    sb = get_supabase()
    res = (
        sb.table("persons")
        .update(
            {
                "police_report_number": payload.police_report_number,
                "verified_police_report": True,
                "last_verified_at": utcnow().isoformat(),
            }
        )
        .eq("id", str(person_id))
        .execute()
    )
    if not res.data:
        raise HTTPException(404, "Person not found")
    return {"person": res.data[0], "badge": "Verified Case"}


@router.post("/persons/{person_id}/renew")
def renew_case(person_id: UUID):
    """90-day family confirmation."""
    sb = get_supabase()
    res = (
        sb.table("persons")
        .update({"last_verified_at": utcnow().isoformat()})
        .eq("id", str(person_id))
        .execute()
    )
    if not res.data:
        raise HTTPException(404, "Person not found")
    return {"ok": True, "last_verified_at": res.data[0].get("last_verified_at")}


@router.post("/persons/{person_id}/flag")
def flag_suspicious(person_id: UUID, payload: FlagPayload):
    sb = get_supabase()
    try:
        sb.table("profile_flags").insert(
            {"person_id": str(person_id), "reason": payload.reason}
        ).execute()
    except Exception as exc:
        raise HTTPException(503, f"profile_flags missing — run migration 003 ({exc})") from exc
    flags = sb.table("profile_flags").select("id").eq("person_id", str(person_id)).execute().data or []
    n = len(flags)
    update = {"suspicious_flags": n}
    if n >= 3:
        update["under_review"] = True
    sb.table("persons").update(update).eq("id", str(person_id)).execute()
    return {"flags": n, "under_review": n >= 3}


@router.get("/persons/{person_id}/clusters")
def list_clusters(person_id: UUID):
    try:
        rows = (
            get_supabase()
            .table("tip_clusters")
            .select("*")
            .eq("person_id", str(person_id))
            .order("created_at", desc=True)
            .execute()
            .data
            or []
        )
        return {"count": len(rows), "clusters": rows}
    except Exception:
        return {"count": 0, "clusters": [], "note": "Run migration 003"}


# -------------------- Backboard memory --------------------

@router.post("/memory/remember")
def memory_remember(payload: MemoryRemember):
    return remember_search(
        payload.participant_key,
        city=payload.city,
        date_from=payload.date_from,
        date_to=payload.date_to,
        filters=payload.filters,
    )


@router.get("/memory/recall")
def memory_recall(participant_key: str = Query(..., min_length=3)):
    return recall_search(participant_key)


@router.delete("/memory/forget")
def memory_forget(participant_key: str = Query(..., min_length=3)):
    return forget_search(participant_key)


# -------------------- ElevenLabs --------------------

@router.post("/persons/{person_id}/audio")
def case_audio(person_id: UUID, payload: AudioRequest):
    sb = get_supabase()
    p = sb.table("persons").select("*").eq("id", str(person_id)).limit(1).execute().data
    if not p:
        raise HTTPException(404, "Person not found")
    person = p[0]
    text = payload.text or (
        f"Missing person alert for {person.get('name')}. "
        f"Age {person.get('age')}. Last seen near {person.get('last_seen_location')} "
        f"on {person.get('last_seen_date')}. {person.get('description')}. "
        f"{person.get('ai_summary') or ''}"
    )
    # Never include emails
    result = synthesize_speech(text)
    result["person_id"] = str(person_id)
    return result


@router.get("/audio/{file_name}")
def get_audio_file(file_name: str):
    safe = Path(file_name).name
    path = CACHE_DIR / safe
    if not path.exists() or not safe.endswith(".mp3"):
        raise HTTPException(404, "Audio not found")
    return FileResponse(path, media_type="audio/mpeg", filename=safe)
