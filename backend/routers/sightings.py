"""
Sighting routes for FindMyPal.

POST /persons/{person_id}/sightings — submit a tip / sighting
GET  /persons/{person_id}/sightings — list all sightings for a person
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from database import get_supabase
from schemas import SightingCreate, SightingListResponse, SightingOut

router = APIRouter(tags=["sightings"])


def _row_to_sighting(row: dict) -> SightingOut:
    """Map a Supabase row dict to the SightingOut schema."""
    return SightingOut(**row)


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

    result = supabase.table("sightings").insert(data).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create sighting",
        )

    return _row_to_sighting(result.data[0])


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
