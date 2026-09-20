"""
Sighting routes for FindMyPal.

POST /persons/{person_id}/sightings — submit a tip / sighting
GET  /persons/{person_id}/sightings — list all sightings for a person
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from database import get_database
from schemas import SightingCreate, SightingListResponse, SightingOut
from services.intelligence import score_sighting_credibility
from services.advanced import (
    detect_tip_cluster,
    match_nl_alerts_against_tip,
    push_live_tip,
    recompute_tips_count,
)
from datetime import datetime

router = APIRouter(tags=["sightings"])


def _row_to_sighting(row: dict) -> SightingOut:
    """Map a SpacetimeDB row dict to the SightingOut schema."""
    # Drop unknown keys so pre-migration rows still validate
    allowed = set(SightingOut.model_fields.keys())
    cleaned = {k: v for k, v in row.items() if k in allowed}
    return SightingOut(**cleaned)


_row_to_sighting_flexible = _row_to_sighting


def _post_sighting_side_effects(database, person_id, payload, row: dict) -> None:
    """Live feed, engagement, NL alerts, tip clustering — best effort."""
    try:
        person = (
            database.table("persons")
            .select("id,name,age,last_seen_location,contact_email")
            .eq("id", str(person_id))
            .limit(1)
            .execute()
            .data
            or [{}]
        )[0]
        pname = person.get("name") or "Unknown"
        push_live_tip(str(person_id), pname, payload.description)
        recompute_tips_count(str(person_id))
        match_nl_alerts_against_tip(payload.description, str(person_id), pname)
        when = payload.date_time
        if isinstance(when, str):
            when = datetime.fromisoformat(when.replace("Z", "+00:00"))
        cluster = detect_tip_cluster(
            str(person_id),
            payload.location_lat,
            payload.location_lng,
            when,
        )
        if cluster:
            row["cluster_alert"] = cluster

        # Additive: EmailJS police / family notify (no-op if env unset)
        try:
            from notifications import (
                notify_family_new_tip_sync,
                notify_police_new_tip_sync,
            )

            tip_payload = {
                "tip_type": row.get("tip_type") or "general",
                "location": f"{payload.location_lat}, {payload.location_lng}",
                "seen_at": str(payload.date_time),
                "date_time": str(payload.date_time),
                "confidence_level": payload.confidence_level,
                "description": payload.description,
                "submitter_email": getattr(payload, "submitter_email", None)
                or row.get("submitter_email"),
            }
            police_ok = notify_police_new_tip_sync(person, tip_payload)
            notify_family_new_tip_sync(person, tip_payload)
            row["police_notified"] = bool(police_ok)
        except Exception:
            row["police_notified"] = False
    except Exception:
        pass


def _ensure_person_exists(person_id: UUID) -> None:
    """Raise 404 if the parent person row is missing."""
    database = get_database()
    result = (
        database.table("persons")
        .select("id")
        .eq("id", str(person_id))
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person {person_id} not found",
        )


@router.post(
    "/persons/{person_id}/sightings",
    response_model=SightingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a sighting / tip for a person",
)
def create_sighting(person_id: UUID, payload: SightingCreate) -> SightingOut:
    """
    Insert a sighting linked to `person_id`.

    Coordinates are stored as lat/lng for the Leaflet map on the profile page.
    Tips are closed once a case is marked found / resolved.
    """
    _ensure_person_exists(person_id)

    database = get_database()
    person_rows = (
        database.table("persons")
        .select("id,status,name")
        .eq("id", str(person_id))
        .limit(1)
        .execute()
        .data
        or []
    )
    case_status = (person_rows[0].get("status") or "").lower() if person_rows else ""
    if case_status in {"found", "closed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This case is already resolved — tips are closed.",
        )

    data = payload.model_dump(mode="json")
    data["person_id"] = str(person_id)

    # EmailStr serializes fine via model_dump; coerce None explicitly
    if data.get("submitter_email") is None:
        data.pop("submitter_email", None)
    if not (data.get("tip_type") or "").strip():
        data.pop("tip_type", None)
    else:
        data["tip_type"] = str(data["tip_type"]).strip()

    # AI / heuristic credibility score (1–10), separate from reporter confidence_level
    scored = score_sighting_credibility(
        description=payload.description,
        location_lat=payload.location_lat,
        location_lng=payload.location_lng,
        date_time=payload.date_time,
        person_id=str(person_id),
    )
    data["credibility_score"] = scored["credibility_score"]
    data["family_review_flag"] = scored["family_review_flag"]
    data["credibility_reasons"] = "; ".join(scored.get("reasons") or [])

    result = database.table("sightings").insert(data).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create sighting",
        )

    row = dict(result.data[0])
    # Ensure response includes scoring even if DB omitted defaults
    row.setdefault("credibility_score", scored["credibility_score"])
    row.setdefault("family_review_flag", scored["family_review_flag"])
    _post_sighting_side_effects(database, person_id, payload, row)
    return _row_to_sighting_flexible(row)


@router.get(
    "/persons/{person_id}/sightings",
    response_model=SightingListResponse,
    summary="List all sightings for a person",
)
def list_sightings(person_id: UUID) -> SightingListResponse:
    """
    Return every sighting for a person, newest first.

    Used by the profile page timeline and the Leaflet map markers.
    """
    _ensure_person_exists(person_id)

    database = get_database()
    result = (
        database.table("sightings")
        .select("*")
        .eq("person_id", str(person_id))
        .order("date_time", desc=True)
        .execute()
    )

    rows = result.data or []
    sightings = [_row_to_sighting(row) for row in rows]

    return SightingListResponse(count=len(sightings), sightings=sightings)
