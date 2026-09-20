"""
Shared helpers for advanced features: email stub, geo, tip clustering.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from database import get_database
from services.geocode import geocode_query

logger = logging.getLogger(__name__)



def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def queue_email(to_email: str, subject: str, body: str, kind: str = "generic", meta: Optional[dict] = None) -> Dict[str, Any]:
    """
    Demo email sender — persists to email_outbox_log when table exists.
    Does not claim SMTP delivery unless SMTP is later configured.
    """
    entry = {
        "to_email": to_email,
        "subject": subject,
        "body": body,
        "kind": kind,
        "meta": meta or {},
        "created_at": utcnow().isoformat(),
        "delivery": "logged_only",
    }
    try:
        get_database().table("email_outbox_log").insert(
            {
                "to_email": to_email,
                "subject": subject,
                "body": body,
                "kind": kind,
                "meta": meta or {},
            }
        ).execute()
        entry["persisted"] = True
    except Exception as exc:  # noqa: BLE001
        logger.info("email_outbox_log unavailable (%s); keeping in-memory only", exc)
        entry["persisted"] = False
    logger.info("EMAIL[%s] → %s | %s", kind, to_email, subject)
    return entry


def push_live_tip(person_id: str, person_name: str, snippet: str) -> Dict[str, Any]:
    event = {
        "id": f"live-{int(utcnow().timestamp()*1000)}",
        "person_id": person_id,
        "person_name": person_name,
        "snippet": (snippet or "")[:180],
        "created_at": utcnow().isoformat(),
    }
    try:
        get_database().table("live_tip_events").insert(
            {
                "person_id": person_id,
                "person_name": person_name,
                "snippet": event["snippet"],
            }
        ).execute()
    except Exception:  # noqa: BLE001
        pass
    return event


def notify_zip_alerts_for_new_case(person: Dict[str, Any]) -> int:
    """Log notifications for zip subscribers near a newly created case."""
    loc = (person.get("last_seen_location") or "").strip()
    if not loc:
        return 0
    hit = geocode_query(loc)
    if not hit:
        return 0
    try:
        rows = (
            get_database()
            .table("alert_subscriptions")
            .select("email,zip_code")
            .eq("kind", "zip")
            .eq("active", True)
            .execute()
            .data
            or []
        )
    except Exception:
        return 0
    sent = 0
    for a in rows:
        z = (a.get("zip_code") or "").strip()
        if not z:
            continue
        zhit = geocode_query(z)
        if not zhit:
            continue
        km = haversine_km(hit["lat"], hit["lng"], zhit["lat"], zhit["lng"])
        if km <= 40:
            queue_email(
                a["email"],
                "FindMyPal — new case near your zip",
                f"A new active case ({person.get('name')}) was reported near {loc} "
                f"(~{km:.0f} km from {z}). This message is logged on the server; "
                "SMTP is not configured unless you add it.",
                kind="zip_alert",
                meta={"person_id": person.get("id"), "zip": z},
            )
            sent += 1
    return sent


def get_live_tips(limit: int = 10) -> List[Dict[str, Any]]:
    try:
        rows = (
            get_database()
            .table("live_tip_events")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        if rows:
            return rows
    except Exception:  # noqa: BLE001
        pass
    try:
        tips = (
            get_database()
            .table("sightings")
            .select("id,person_id,description,created_at")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        out = []
        for t in tips:
            name = "Case"
            try:
                p = (
                    get_database()
                    .table("persons")
                    .select("name")
                    .eq("id", t["person_id"])
                    .limit(1)
                    .execute()
                    .data
                    or []
                )
                if p:
                    name = p[0].get("name") or name
            except Exception:
                pass
            out.append(
                {
                    "id": t.get("id"),
                    "person_id": t.get("person_id"),
                    "person_name": name,
                    "snippet": (t.get("description") or "")[:180],
                    "created_at": t.get("created_at"),
                }
            )
        return out
    except Exception:
        return []


def recompute_tips_count(person_id: str) -> int:
    sb = get_database()
    rows = sb.table("sightings").select("id").eq("person_id", person_id).execute().data or []
    n = len(rows)
    try:
        sb.table("persons").update({"tips_count": n}).eq("id", person_id).execute()
    except Exception:  # noqa: BLE001
        pass
    return n


def detect_tip_cluster(person_id: str, lat: float, lng: float, when: datetime) -> Optional[Dict[str, Any]]:
    """
    If 3+ tips fall within ~1.5km and 48 hours, create a cluster alert.
    """
    sb = get_database()
    rows = (
        sb.table("sightings")
        .select("*")
        .eq("person_id", person_id)
        .order("date_time", desc=True)
        .limit(50)
        .execute()
        .data
        or []
    )
    window = timedelta(hours=48)
    when = when if when.tzinfo else when.replace(tzinfo=timezone.utc)
    nearby = []
    for r in rows:
        try:
            dt = datetime.fromisoformat(str(r["date_time"]).replace("Z", "+00:00"))
        except Exception:  # noqa: BLE001
            continue
        if abs((dt - when).total_seconds()) > window.total_seconds():
            continue
        d = haversine_km(lat, lng, float(r["location_lat"]), float(r["location_lng"]))
        if d <= 1.5:
            nearby.append(r)

    if len(nearby) < 3:
        return None

    cluster = {
        "person_id": person_id,
        "center_lat": lat,
        "center_lng": lng,
        "radius_km": 1.5,
        "tip_count": len(nearby),
        "window_start": (when - window).isoformat(),
        "window_end": when.isoformat(),
        "label": f"High activity: {len(nearby)} tips near this area within 48h",
        "notified": False,
    }
    try:
        inserted = sb.table("tip_clusters").insert(cluster).execute()
        cluster_row = (inserted.data or [cluster])[0]
    except Exception as exc:  # noqa: BLE001
        logger.warning("tip_clusters insert failed: %s", exc)
        cluster_row = cluster

    # Notify case watchers / coordinators
    try:
        person = sb.table("persons").select("name").eq("id", person_id).limit(1).execute().data
        name = (person or [{}])[0].get("name") or "a case"
        watchers = (
            sb.table("alert_subscriptions")
            .select("email")
            .eq("person_id", person_id)
            .eq("active", True)
            .execute()
            .data
            or []
        )
        coords = (
            sb.table("case_coordinators").select("email").eq("person_id", person_id).execute().data or []
        )
        recipients = {w["email"] for w in watchers if w.get("email")} | {
            c["email"] for c in coords if c.get("email")
        }
        for email in recipients:
            queue_email(
                email,
                f"Cluster alert: {name}",
                cluster["label"] + f"\nApprox: {lat:.4f}, {lng:.4f}",
                kind="cluster_alert",
                meta={"person_id": person_id},
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("cluster notify failed: %s", exc)

    return cluster_row


def match_nl_alerts_against_tip(description: str, person_id: str, person_name: str) -> List[Dict[str, Any]]:
    """Very simple keyword overlap matcher for NL alert queries."""
    try:
        alerts = (
            get_database()
            .table("alert_subscriptions")
            .select("*")
            .eq("kind", "natural_language")
            .eq("active", True)
            .execute()
            .data
            or []
        )
    except Exception:  # noqa: BLE001
        return []

    desc_l = (description or "").lower()
    name_l = (person_name or "").lower()
    hit = []
    for a in alerts:
        q = (a.get("query_text") or "").lower()
        if not q:
            continue
        tokens = [t for t in q.replace(",", " ").split() if len(t) > 3]
        if not tokens:
            continue
        score = sum(1 for t in tokens if t in desc_l or t in name_l)
        if score >= max(2, len(tokens) // 3):
            queue_email(
                a["email"],
                "FindMyPal alert matched a new tip",
                f"Your alert: {a.get('query_text')}\n\nCase: {person_name}\nTip: {description[:400]}",
                kind="nl_alert",
                meta={"alert_id": a.get("id"), "person_id": person_id},
            )
            hit.append(a)
    return hit


def city_dashboard_stats() -> Dict[str, Any]:
    """Aggregate public stats — no private emails."""
    sb = get_database()
    try:
        persons = sb.table("persons").select("id,status,last_seen_location,created_at,found_at").execute().data or []
    except Exception:
        persons = sb.table("persons").select("id,status,last_seen_location,created_at").execute().data or []
    active = [p for p in persons if (p.get("status") or "").lower() == "active"]
    found = [p for p in persons if (p.get("status") or "").lower() == "found"]
    # crude month resolution
    now = utcnow()
    month_found = 0
    for p in found:
        fa = p.get("found_at") or p.get("created_at")
        if not fa:
            continue
        try:
            dt = datetime.fromisoformat(str(fa).replace("Z", "+00:00"))
            if dt.year == now.year and dt.month == now.month:
                month_found += 1
        except Exception:  # noqa: BLE001
            pass

    # location frequency (city-ish: first segment before comma)
    from collections import Counter

    locs = Counter()
    for p in active:
        loc = (p.get("last_seen_location") or "Unknown").split(",")[0].strip()
        locs[loc] += 1

    return {
        "active_cases": len(active),
        "found_cases": len(found),
        "total_cases": len(persons),
        "resolved_this_month": month_found,
        "resolution_rate_all_time": round(len(found) / max(len(persons), 1), 3),
        "top_last_seen_areas": [{"area": a, "count": c} for a, c in locs.most_common(8)],
        "note": "Aggregate public patterns only - no personal tip content.",
    }


def cross_case_patterns(radius_km: float = 2.0) -> Dict[str, Any]:
    """
    Snowflake-style cross-case geographic pattern detection.
    Uses SpacetimeDB case data locally when Snowflake is not configured.
    Labeled provenance: local_projection (not NamUs / not live Snowflake).
    """
    sb = get_database()
    persons = (
        sb.table("persons")
        .select("id,name,status,last_seen_location")
        .eq("status", "active")
        .execute()
        .data
        or []
    )
    # Use first sighting or skip if no coords — geocode not here; use sightings centroids
    tips = sb.table("sightings").select("person_id,location_lat,location_lng,date_time").execute().data or []
    by_person: Dict[str, List] = {}
    for t in tips:
        by_person.setdefault(t["person_id"], []).append(t)

    centers = []
    name_by_id = {p["id"]: p.get("name") for p in persons}
    for pid, plist in by_person.items():
        if pid not in name_by_id:
            continue
        lat = sum(float(x["location_lat"]) for x in plist) / len(plist)
        lng = sum(float(x["location_lng"]) for x in plist) / len(plist)
        centers.append({"person_id": pid, "name": name_by_id[pid], "lat": lat, "lng": lng})

    clusters = []
    used = set()
    for i, a in enumerate(centers):
        if a["person_id"] in used:
            continue
        group = [a]
        for b in centers[i + 1 :]:
            if b["person_id"] in used:
                continue
            if haversine_km(a["lat"], a["lng"], b["lat"], b["lng"]) <= radius_km:
                group.append(b)
        if len(group) >= 2:
            for g in group:
                used.add(g["person_id"])
            clusters.append(
                {
                    "count": len(group),
                    "radius_km": radius_km,
                    "cases": [{"person_id": g["person_id"], "name": g["name"]} for g in group],
                    "center": {
                        "lat": sum(g["lat"] for g in group) / len(group),
                        "lng": sum(g["lng"] for g in group) / len(group),
                    },
                    "summary": f"{len(group)} active cases have tip activity within ~{radius_km} miles/km of each other",
                }
            )

    return {
        "provenance": "spacetimedb_projection",
        "snowflake": "unavailable",
        "note": "Not a Snowflake warehouse query and not NamUs data. Demonstrates cross-case geographic clustering on demo cases.",
        "clusters": clusters,
    }


def activity_buckets(person_id: str, bucket_hours: int = 24) -> Dict[str, Any]:
    rows = (
        get_database()
        .table("sightings")
        .select("date_time,created_at,credibility_score")
        .eq("person_id", person_id)
        .order("date_time")
        .execute()
        .data
        or []
    )
    buckets: Dict[str, int] = {}
    for r in rows:
        raw = r.get("date_time") or r.get("created_at")
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except Exception:  # noqa: BLE001
            continue
        # floor to bucket
        epoch = int(dt.timestamp())
        step = bucket_hours * 3600
        key_ts = epoch - (epoch % step)
        key = datetime.fromtimestamp(key_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        buckets[key] = buckets.get(key, 0) + 1
    series = [{"bucket": k, "tips": v} for k, v in sorted(buckets.items())]
    return {
        "person_id": person_id,
        "bucket_hours": bucket_hours,
        "series": series,
        "total_tips": len(rows),
        "provenance": "spacetimedb_sightings",
        "marimo": "embed_via_frontend_charts",
        "note": "React activity explorer uses this API. Optional marimo notebook can consume the same route.",
    }
