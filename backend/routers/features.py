"""
Advanced feature routes: alerts, live feed, clusters, engagement, found flow,
coordinators, social kit data, dashboard, patterns, audio, search memory.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel, EmailStr, Field

from database import get_database
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
from services.heatmap import (
    BALTIMORE_BBOX,
    anonymized_tip_points,
    build_folium_heatmap_html,
    in_baltimore_bbox,
    points_from_lookup_locations,
    points_from_sighting_rows,
)
from routers.persons import _row_to_person
from services.baltimore_cameras import (
    CAMERAS_URL,
    DISCLAIMER as BALTIMORE_DISCLAIMER,
    HOW_TO_USE as BALTIMORE_HOW_TO,
    fetch_cameras,
    nearest_to_point,
)
from services.geocode import geocode_query
from services.owner_auth import require_owner
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
    """HTTP snapshot of the persistent tip feed; browser uses native subscriptions."""
    tips = get_live_tips(limit)
    return {
        "tips": tips,
        "transport": "http_snapshot",
        "spacetime": "primary_database",
        "note": "Stored in SpacetimeDB. The homepage receives updates through a native subscription.",
    }


@router.get("/geo/search")
def geo_search(q: str = Query(..., min_length=2, max_length=500)):
    """Backend Nominatim proxy — browsers cannot call OSM Nominatim reliably (CORS/UA)."""
    hit = geocode_query(q)
    if not hit:
        return {"found": False, "query": q}
    return {"found": True, "query": q, **hit}


@router.get("/dashboard/city")
def dashboard_city():
    return city_dashboard_stats()


@router.get("/analytics/case-activity/{person_id}")
def case_activity(person_id: UUID, bucket_hours: int = Query(24, ge=1, le=168)):
    return activity_buckets(str(person_id), bucket_hours=bucket_hours)


@router.get("/analytics/heatmap/{person_id}")
def case_heatmap_data(person_id: UUID):
    """
    JSON points for the marimo / Folium density heatmap.
    Provenance: community tips for this case (not NamUs).
    """
    rows = (
        get_database()
        .table("sightings")
        .select("id,location_lat,location_lng,description,date_time,credibility_score,created_at")
        .eq("person_id", str(person_id))
        .execute()
        .data
        or []
    )
    points = points_from_sighting_rows(rows)
    return {
        "person_id": str(person_id),
        "count": len(points),
        "points": points,
        "provenance": "community_tips",
        "marimo": "notebooks/sightings_heatmap.py",
        "embed_path": f"/analytics/heatmap/{person_id}/embed",
    }


@router.get("/analytics/baltimore/civic")
def baltimore_civic_meta():
    """
    Metadata for the Baltimore civic-context marimo story.
    Does not invent case facts — cameras are public infrastructure points.
    """
    return {
        "title": "Baltimore civic context",
        "story": (
            "Layer 1: anonymized tip density across all active FindMyPal cases. "
            "Layer 2: public CitiWatch camera locations. "
            "Compare clusters vs cameras for volunteer search coordination — "
            "not investigation proof."
        ),
        "disclaimer": (
            "Camera locations are public infrastructure, not live video. "
            "Tip layer is lat/lng density only (no names). Community tips are unverified. "
            "Gaps in camera coverage near tip clusters suggest where volunteers may focus."
        ),
        "marimo_notebook": "notebooks/baltimore_civic_story.py",
        "run": "marimo run notebooks/baltimore_civic_story.py",
        "edit": "marimo edit notebooks/baltimore_civic_story.py",
        "open_data": {
            "citiwatch_cameras": (
                "https://geodata.baltimorecity.gov/egis/rest/services/"
                "CityView/CitiWatchCamera/FeatureServer/0"
            ),
            "portal": "https://data.baltimorecity.gov/datasets/baltimore::citiwatch-camera-locations",
        },
        "tip_clusters": "/analytics/baltimore/tip-clusters",
        "tip_overlay": "/analytics/heatmap/{person_id}",
        "cameras_proxy": "/analytics/baltimore/cameras",
    }


@router.get("/analytics/baltimore/tip-clusters")
def baltimore_tip_clusters(
    baltimore_only: bool = Query(
        True,
        description="If true, keep only tips inside an approximate Baltimore metro box",
    ),
):
    """
    Layer 1 for civic maps: anonymized tip density across all *active* cases.

    Returns lat/lng/weight only — no names, descriptions, emails, or tip ids.
    """
    sb = get_database()
    active = (
        sb.table("persons")
        .select("id")
        .eq("status", "active")
        .execute()
        .data
        or []
    )
    active_ids = [str(p["id"]) for p in active if p.get("id")]
    if not active_ids:
        return {
            "count": 0,
            "points": [],
            "active_cases": 0,
            "baltimore_only": baltimore_only,
            "bbox": BALTIMORE_BBOX,
            "provenance": "community_tips_active_cases_anonymized",
            "privacy": "no names, descriptions, emails, or tip ids",
            "marimo": "notebooks/baltimore_civic_story.py",
        }

    # Supabase .in_ with many UUIDs is fine for hackathon scale
    rows = (
        sb.table("sightings")
        .select("location_lat,location_lng,credibility_score,person_id")
        .in_("person_id", active_ids)
        .execute()
        .data
        or []
    )

    all_points = anonymized_tip_points(rows)
    if baltimore_only:
        points = [
            p
            for p in all_points
            if in_baltimore_bbox(float(p["lat"]), float(p["lng"]))
        ]
    else:
        points = all_points

    return {
        "count": len(points),
        "count_all_active_tips": len(all_points),
        "points": points,
        "active_cases": len(active_ids),
        "baltimore_only": baltimore_only,
        "bbox": BALTIMORE_BBOX if baltimore_only else None,
        "provenance": "community_tips_active_cases_anonymized",
        "privacy": "no names, descriptions, emails, or tip ids",
        "marimo": "notebooks/baltimore_civic_story.py",
    }


@router.get("/analytics/baltimore/cameras")
def baltimore_citiwatch_cameras(limit: int = Query(500, ge=1, le=2000)):
    """
    Proxy Baltimore CitiWatch camera points (WGS84) for notebooks / demos.
    Locations only — not live video.
    """
    try:
        cameras = fetch_cameras(limit=limit)
    except Exception as exc:
        raise HTTPException(
            503,
            f"Baltimore GIS unavailable ({exc}). Try the marimo notebook later.",
        ) from exc
    return {
        "count": len(cameras),
        "cameras": cameras,
        "provenance": "baltimore_citiwatch_feature_server",
        "source": CAMERAS_URL,
        "disclaimer": BALTIMORE_DISCLAIMER,
        "marimo": "notebooks/baltimore_civic_story.py",
    }


@router.get("/analytics/baltimore/nearest/{person_id}")
def baltimore_nearest_for_case(
    person_id: UUID,
    k: int = Query(3, ge=1, le=5),
    max_m: float = Query(2500, ge=200, le=8000),
):
    """
    Soft suggestions: nearest listed CitiWatch cameras to each tip / last-seen.
    Distance-based only — not AI watching feeds or face match on CCTV.
    """
    try:
        cameras = fetch_cameras(limit=1200)
    except Exception as exc:
        raise HTTPException(503, f"Baltimore GIS unavailable ({exc})") from exc

    sb = get_database()
    person_rows = (
        sb.table("persons")
        .select("id,name,last_seen_location,last_seen_date")
        .eq("id", str(person_id))
        .limit(1)
        .execute()
        .data
        or []
    )
    if not person_rows:
        raise HTTPException(404, "Person not found")
    person = person_rows[0]

    tips_rows = (
        sb.table("sightings")
        .select("id,location_lat,location_lng,description,date_time")
        .eq("person_id", str(person_id))
        .execute()
        .data
        or []
    )

    tip_results = []
    for row in tips_rows:
        try:
            lat = float(row.get("location_lat"))
            lng = float(row.get("location_lng"))
        except (TypeError, ValueError):
            continue
        tip_results.append(
            {
                "tip_id": row.get("id"),
                "lat": lat,
                "lng": lng,
                "date_time": row.get("date_time"),
                "snippet": (row.get("description") or "")[:160],
                "nearest_cameras": nearest_to_point(lat, lng, cameras, k=k, max_m=max_m),
            }
        )

    last_seen_block = None
    loc = (person.get("last_seen_location") or "").strip()
    if loc:
        geo = geocode_query(loc)
        if geo and geo.get("lat") is not None and geo.get("lng") is not None:
            lat, lng = float(geo["lat"]), float(geo["lng"])
            last_seen_block = {
                "query": loc,
                "lat": lat,
                "lng": lng,
                "note": "Geocoded last-seen place is approximate (often city/neighborhood level).",
                "nearest_cameras": nearest_to_point(lat, lng, cameras, k=k, max_m=max_m),
            }

    return {
        "person_id": str(person_id),
        "person_name": person.get("name"),
        "camera_catalog_count": len(cameras),
        "disclaimer": BALTIMORE_DISCLAIMER,
        "how_to_use": BALTIMORE_HOW_TO,
        "last_seen": last_seen_block,
        "tips": tip_results,
        "tips_with_cameras": sum(1 for t in tip_results if t["nearest_cameras"]),
        "provenance": "baltimore_citiwatch_locations + community_tips",
        "marimo": "notebooks/baltimore_civic_story.py",
        "face_match_note": (
            "Face matching is only available on Lookup / tip photos you provide — "
            "not on city camera feeds."
        ),
    }


@router.get("/analytics/heatmap/{person_id}/embed", response_class=HTMLResponse)
def case_heatmap_embed(person_id: UUID):
    """Folium HeatMap HTML for iframe embed (same viz as the marimo notebook)."""
    person = (
        get_database()
        .table("persons")
        .select("name")
        .eq("id", str(person_id))
        .limit(1)
        .execute()
        .data
        or [{}]
    )[0]
    rows = (
        get_database()
        .table("sightings")
        .select("id,location_lat,location_lng,description,date_time,credibility_score,created_at")
        .eq("person_id", str(person_id))
        .execute()
        .data
        or []
    )
    points = points_from_sighting_rows(rows)
    name = person.get("name") or "Case"
    html = build_folium_heatmap_html(
        points,
        title=f"Live sightings heatmap · {name}",
        zoom_start=12 if points else 6,
    )
    return HTMLResponse(content=html)


class HeatmapEmbedBody(BaseModel):
    title: str = Field("Location heatmap", max_length=200)
    points: List[Dict[str, Any]] = Field(default_factory=list)


@router.post("/analytics/heatmap/embed", response_class=HTMLResponse)
def heatmap_embed_from_points(payload: HeatmapEmbedBody):
    """
    Build a Folium density heatmap from arbitrary points
    (used by Lookup report / marimo for public-web mention locations).
    """
    points = points_from_lookup_locations(payload.points) if payload.points else []
    # Allow raw lat/lng/weight payloads too
    if not points and payload.points:
        points = list(payload.points)
    html = build_folium_heatmap_html(
        points,
        title=payload.title,
        zoom_start=5 if len(points) > 3 else 10,
    )
    return HTMLResponse(content=html)


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
        get_database()
        .table("sightings")
        .select("description")
        .eq("person_id", str(person_id))
        .execute()
        .data
        or []
    )
    counts = {
        "community_tips": len(rows),
        "reddit": 0,
        "instagram": 0,
        "facebook": 0,
        "news": 0,
        "x": 0,
        "other": 0,
    }
    for r in rows:
        t = (r.get("description") or "").lower()
        if "reddit" in t:
            counts["reddit"] += 1
        elif "instagram" in t or "insta" in t:
            counts["instagram"] += 1
        elif "facebook" in t or "fb.com" in t:
            counts["facebook"] += 1
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
        res = get_database().table("alert_subscriptions").insert(row).execute()
        return {"ok": True, "alert": (res.data or [row])[0]}
    except Exception as exc:
        raise HTTPException(503, f"Alerts table unavailable — check SpacetimeDB connectivity and module publication. ({exc})") from exc


@router.post("/alerts/zip")
def create_zip_alert(payload: ZipAlertCreate):
    row = {
        "kind": "zip",
        "email": str(payload.email),
        "zip_code": payload.zip_code,
        "active": True,
    }
    try:
        res = get_database().table("alert_subscriptions").insert(row).execute()
        return {"ok": True, "alert": (res.data or [row])[0]}
    except Exception as exc:
        raise HTTPException(503, f"Alerts table unavailable — check SpacetimeDB connectivity and module publication. ({exc})") from exc


@router.post("/alerts/watch")
def watch_case(payload: CaseWatchCreate):
    sb = get_database()
    pid = str(payload.person_id)
    email = str(payload.email)
    try:
        existing = (
            sb.table("alert_subscriptions")
            .select("id,email")
            .eq("kind", "case_watch")
            .eq("person_id", pid)
            .eq("active", True)
            .execute()
            .data
            or []
        )
        person = sb.table("persons").select("watchers_count").eq("id", pid).limit(1).execute().data
        n = int((person or [{}])[0].get("watchers_count") or 0)
        if any((x.get("email") or "").lower() == email.lower() for x in existing):
            return {"ok": True, "already_watching": True, "watchers_count": n}
        row = {
            "kind": "case_watch",
            "email": email,
            "person_id": pid,
            "active": True,
        }
        try:
            res = sb.table("alert_subscriptions").insert(row).execute()
        except Exception as ins_exc:
            msg = str(ins_exc).lower()
            if "unique" in msg or "duplicate" in msg:
                return {"ok": True, "already_watching": True, "watchers_count": n}
            raise
        n = n + 1
        sb.table("persons").update({"watchers_count": n}).eq("id", pid).execute()
        return {"ok": True, "alert": (res.data or [row])[0], "watchers_count": n}
    except Exception as exc:
        raise HTTPException(503, f"Watch unavailable — check SpacetimeDB connectivity and module publication. ({exc})") from exc


# -------------------- case management --------------------

@router.get("/persons/{person_id}/engagement")
def engagement(person_id: UUID):
    sb = get_database()
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
    sb = get_database()
    p = sb.table("persons").select("shares_count").eq("id", str(person_id)).limit(1).execute().data
    if not p:
        raise HTTPException(404, "Person not found")
    current = sb.table("persons").select("shares_count").eq("id", str(person_id)).limit(1).execute().data
    if not current:
        raise HTTPException(status_code=404, detail="Person not found")
    result = sb.table("persons").update(
        {"shares_count": int(current[0].get("shares_count") or 0) + 1}
    ).eq("id", str(person_id)).execute()
    return {"shares_count": result.data[0]["shares_count"]}


@router.get("/persons/{person_id}/social-kit")
def social_kit(person_id: UUID):
    sb = get_database()
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
def add_case_update(
    person_id: UUID,
    payload: CaseUpdateCreate,
    x_owner_token: Optional[str] = Header(None, alias="X-Owner-Token"),
):
    require_owner(person_id, x_owner_token)
    sb = get_database()
    row = {
        "person_id": str(person_id),
        "body": payload.body,
        "author_email": str(payload.author_email) if payload.author_email else None,
    }
    try:
        res = sb.table("case_updates").insert(row).execute()
    except Exception as exc:
        raise HTTPException(503, f"case_updates missing — check SpacetimeDB connectivity and module publication ({exc})") from exc

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
            get_database()
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
        return {"count": 0, "updates": [], "note": "SpacetimeDB unavailable"}


class SourceLinkCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=8, max_length=2000)
    source_type: str = Field("other", max_length=40)
    published_at: Optional[str] = None


def _validate_http_url(url: str) -> str:
    s = (url or "").strip()
    low = s.lower()
    if not (low.startswith("http://") or low.startswith("https://")):
        raise HTTPException(400, "URL must start with http:// or https://")
    return s


@router.get("/persons/{person_id}/sources")
def list_case_sources(person_id: UUID):
    """Read-only source library for a case (migration 005)."""
    try:
        rows = (
            get_database()
            .table("case_source_links")
            .select("*")
            .eq("person_id", str(person_id))
            .order("created_at", desc=True)
            .execute()
            .data
            or []
        )
        return {"count": len(rows), "sources": rows}
    except Exception:
        return {"count": 0, "sources": [], "note": "Run migration 005 for case_source_links"}


@router.post("/persons/{person_id}/sources")
def add_case_source(
    person_id: UUID,
    payload: SourceLinkCreate,
    x_owner_token: Optional[str] = Header(None, alias="X-Owner-Token"),
):
    """Owner-only add to the small source library (requires X-Owner-Token when set)."""
    require_owner(person_id, x_owner_token)
    url = _validate_http_url(payload.url)
    st = (payload.source_type or "other").strip().lower()
    if st not in {"agency_listing", "news_article", "public_appeal", "other"}:
        st = "other"
    row = {
        "person_id": str(person_id),
        "title": payload.title.strip()[:200],
        "url": url,
        "source_type": st,
        "published_at": payload.published_at or None,
    }
    try:
        res = get_database().table("case_source_links").insert(row).execute()
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg:
            raise HTTPException(409, "This URL is already linked to the case") from exc
        raise HTTPException(503, f"case_source_links missing — run migration 005 ({exc})") from exc
    return {"source": (res.data or [row])[0]}


@router.post("/persons/{person_id}/coordinators")
def invite_coordinator(
    person_id: UUID,
    payload: CoordinatorInvite,
    x_owner_token: Optional[str] = Header(None, alias="X-Owner-Token"),
):
    require_owner(person_id, x_owner_token)
    # Cap at 4 coordinators + implicit owner
    sb = get_database()
    existing = sb.table("case_coordinators").select("id").eq("person_id", str(person_id)).execute().data or []
    if len(existing) >= 4:
        raise HTTPException(400, "Maximum 4 coordinators per case")
    row = {"person_id": str(person_id), "email": str(payload.email), "role": payload.role}
    try:
        res = sb.table("case_coordinators").insert(row).execute()
    except Exception as exc:
        raise HTTPException(503, f"coordinators table missing — check SpacetimeDB connectivity and module publication ({exc})") from exc
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
            get_database()
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
def mark_found(
    person_id: UUID,
    payload: FoundPayload,
    x_owner_token: Optional[str] = Header(None, alias="X-Owner-Token"),
):
    require_owner(person_id, x_owner_token)
    sb = get_database()
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
    return {
        "person": _row_to_person(res.data[0], public=True),
        "thank_you_emails_logged": len(thanked),
    }


@router.post("/persons/{person_id}/verify-police")
def verify_police(
    person_id: UUID,
    payload: VerifyPayload,
    x_owner_token: Optional[str] = Header(None, alias="X-Owner-Token"),
):
    require_owner(person_id, x_owner_token)
    number = (payload.police_report_number or "").strip()
    if not number:
        raise HTTPException(400, "Police report number is required to verify")
    sb = get_database()
    res = (
        sb.table("persons")
        .update(
            {
                "police_report_number": number,
                "verified_police_report": True,
                "last_verified_at": utcnow().isoformat(),
            }
        )
        .eq("id", str(person_id))
        .execute()
    )
    if not res.data:
        raise HTTPException(404, "Person not found")
    return {"person": _row_to_person(res.data[0], public=True), "badge": "Verified Case"}


@router.post("/persons/{person_id}/renew")
def renew_case(
    person_id: UUID,
    x_owner_token: Optional[str] = Header(None, alias="X-Owner-Token"),
):
    """90-day family confirmation."""
    require_owner(person_id, x_owner_token)
    sb = get_database()
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
    sb = get_database()
    try:
        sb.table("profile_flags").insert(
            {"person_id": str(person_id), "reason": payload.reason}
        ).execute()
    except Exception as exc:
        raise HTTPException(503, f"profile_flags missing — check SpacetimeDB connectivity and module publication ({exc})") from exc
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
            get_database()
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
        return {"count": 0, "clusters": [], "note": "SpacetimeDB unavailable"}


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
def case_audio(
    person_id: UUID,
    payload: AudioRequest,
    x_owner_token: Optional[str] = Header(None, alias="X-Owner-Token"),
):
    require_owner(person_id, x_owner_token)
    sb = get_database()
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
