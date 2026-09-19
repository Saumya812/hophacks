"""
Person routes for FindMyPal.

POST   /persons              — create a missing-person profile
GET    /persons              — list / filter profiles
GET    /persons/{person_id}  — single profile
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from database import get_supabase
from schemas import PersonCreate, PersonListResponse, PersonOut

router = APIRouter(tags=["persons"])


def _row_to_person(row: dict) -> PersonOut:
    """Map a Supabase row dict to the PersonOut schema."""
    allowed = set(PersonOut.model_fields.keys())
    cleaned = {k: v for k, v in row.items() if k in allowed}
    return PersonOut(**cleaned)


@router.post(
    "/persons",
    response_model=PersonOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a missing-person profile",
)
def create_person(payload: PersonCreate) -> PersonOut:
    """
    Insert a new row into `persons`.

    Auth is mocked — any caller can create a profile in v1.
    """
    supabase = get_supabase()
    data = payload.model_dump(mode="json")

    result = supabase.table("persons").insert(data).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create person profile",
        )

    return _row_to_person(result.data[0])


@router.get(
    "/persons",
    response_model=PersonListResponse,
    summary="List missing-person profiles with optional filters",
)
def list_persons(
    name: Optional[str] = Query(
        None,
        description="Case-insensitive partial match on name",
        examples=["jane"],
    ),
    location: Optional[str] = Query(
        None,
        description="Case-insensitive partial match on last_seen_location",
        examples=["baltimore"],
    ),
    age_min: Optional[int] = Query(
        None,
        ge=0,
        le=150,
        description="Minimum age (inclusive). Use with age_max for age_range.",
    ),
    age_max: Optional[int] = Query(
        None,
        ge=0,
        le=150,
        description="Maximum age (inclusive). Use with age_min for age_range.",
    ),
    status_filter: Optional[str] = Query(
        "active",
        alias="status",
        description="Filter by case status: active | found | closed | all",
    ),
) -> PersonListResponse:
    """
    Return persons matching the given filters.

    age_min + age_max together implement the age_range filter from the spec.
    Pass status=all to skip the status filter.
    """
    if age_min is not None and age_max is not None and age_max < age_min:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="age_max must be greater than or equal to age_min",
        )

    supabase = get_supabase()
    query = supabase.table("persons").select("*")

    if name:
        # PostgREST ilike syntax: *term* → %term%
        query = query.ilike("name", f"%{name}%")

    if location:
        query = query.ilike("last_seen_location", f"%{location}%")

    if age_min is not None:
        query = query.gte("age", age_min)

    if age_max is not None:
        query = query.lte("age", age_max)

    if status_filter and status_filter.lower() != "all":
        query = query.eq("status", status_filter.lower())

    # Newest cases first
    query = query.order("created_at", desc=True)

    result = query.execute()
    rows = result.data or []
    persons = [_row_to_person(row) for row in rows]

    return PersonListResponse(count=len(persons), persons=persons)


@router.get(
    "/persons/{person_id}",
    response_model=PersonOut,
    summary="Get a single missing-person profile",
)
def get_person(person_id: UUID) -> PersonOut:
    """Fetch one person by UUID primary key."""
    supabase = get_supabase()
    result = (
        supabase.table("persons")
        .select("*")
        .eq("id", str(person_id))
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person {person_id} not found",
        )

    return _row_to_person(result.data[0])
