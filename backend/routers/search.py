"""
Natural-language search route for FindMyPal.

POST /search/natural — Gemini parses the query into filters, then we
run the same Supabase query path as GET /persons (no raw SQL execution).
"""

from fastapi import APIRouter, HTTPException, status

from database import get_supabase
from schemas import (
    NaturalSearchRequest,
    NaturalSearchResponse,
    PersonOut,
)
from services.gemini import query_to_filters

router = APIRouter(tags=["search"])


@router.post(
    "/search/natural",
    response_model=NaturalSearchResponse,
    summary="Search persons with a natural-language query (Gemini)",
)
def natural_search(payload: NaturalSearchRequest) -> NaturalSearchResponse:
    """
    Pipeline:
      1. Send the free-text query to Gemini.
      2. Parse the response into NaturalSearchFilters.
      3. Apply those filters via the Supabase query builder.
      4. Return matching persons plus the inferred filters (for UI transparency).
    """
    try:
        filters = query_to_filters(payload.query)
    except RuntimeError as exc:
        # Missing / invalid API key configuration
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini could not produce usable filters: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001 — surface unexpected Gemini failures
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini request failed: {exc}",
        ) from exc

    supabase = get_supabase()
    query = supabase.table("persons").select("*")

    if filters.name:
        query = query.ilike("name", f"%{filters.name}%")

    if filters.location:
        query = query.ilike("last_seen_location", f"%{filters.location}%")

    if filters.age_min is not None:
        query = query.gte("age", filters.age_min)

    if filters.age_max is not None:
        query = query.lte("age", filters.age_max)

    if filters.status:
        query = query.eq("status", filters.status)

    if filters.gender:
        query = query.ilike("gender", f"%{filters.gender}%")

    query = query.order("created_at", desc=True)
    result = query.execute()
    rows = result.data or []
    persons = [PersonOut(**row) for row in rows]

    return NaturalSearchResponse(
        query=payload.query,
        filters=filters,
        count=len(persons),
        persons=persons,
    )
