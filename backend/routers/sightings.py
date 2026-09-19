"""
Sighting routes for FindMyPal.

POST /persons/{person_id}/sightings — submit a tip / sighting
GET  /persons/{person_id}/sightings — list all sightings for a person
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from database import get_supabase
from schemas import SightingCreate, SightingListResponse, SightingOut
from services.intelligence import score_sighting_credibility

router = APIRouter(tags=["sightings"])


def _row_to_sighting(row: dict) -> SightingOut:
    """Map a Supabase row dict to the SightingOut schema."""
    # Drop unknown keys so pre-migration rows still validate
    allowed = set(SightingOut.model_fields.keys())
    cleaned = {k: v for k, v in row.items() if k in allowed}
    return SightingOut(**cleaned)


_row_to_sighting_flexible = _row_to_sighting


def _ensure_person_exists(person_id: UUID) -> None:
    """Raise 404 if the parent person row is missing."""
    supabase = get_supabase()
    result = (
        supabase.table("persons")
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
    """
    _ensure_person_exists(person_id)

    supabase = get_supabase()
    data = payload.model_dump(mode="json")
    data["person_id"] = str(person_id)

    # EmailStr serializes fine via model_dump; coerce None explicitly
    if data.get("submitter_email") is None:
        data.pop("submitter_email", None)

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

    try:
        result = supabase.table("sightings").insert(data).execute()
    except Exception:
        # Columns may be missing before migration 002 — insert without them
        data.pop("credibility_score", None)
        data.pop("family_review_flag", None)
        data.pop("credibility_reasons", None)
        result = supabase.table("sightings").insert(data).execute()
        if result.data:
            row = dict(result.data[0])
            row.update(scored)
            row["credibility_reasons"] = "; ".join(scored.get("reasons") or [])
            return _row_to_sighting_flexible(row)
        raise

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create sighting",
        )

    row = dict(result.data[0])
    # Ensure response includes scoring even if DB omitted defaults
    row.setdefault("credibility_score", scored["credibility_score"])
    row.setdefault("family_review_flag", scored["family_review_flag"])
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

    supabase = get_supabase()
    result = (
        supabase.table("sightings")
        .select("*")
        .eq("person_id", str(person_id))
        .order("date_time", desc=True)
        .execute()
    )

    rows = result.data or []
    sightings = [_row_to_sighting(row) for row in rows]

    return SightingListResponse(count=len(sightings), sightings=sightings)
