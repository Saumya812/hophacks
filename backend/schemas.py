"""
Pydantic request / response models for the FindMyPal API.

These mirror the columns in db/schema.sql and define validation
for every public route.
"""

from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Persons
# ---------------------------------------------------------------------------

PersonStatus = Literal["active", "found", "closed"]


class PersonCreate(BaseModel):
    """Body for POST /persons — create a missing-person profile."""

    name: str = Field(..., min_length=1, max_length=200, examples=["Jane Doe"])
    age: int = Field(..., ge=0, le=150, examples=[34])
    gender: Optional[str] = Field(None, max_length=50, examples=["female"])
    last_seen_location: str = Field(
        ...,
        min_length=1,
        max_length=500,
        examples=["Baltimore, MD — Inner Harbor"],
    )
    last_seen_date: date = Field(..., examples=["2026-03-01"])
    description: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        examples=["5'6\", brown hair, last seen wearing a red jacket."],
    )
    photo_url: Optional[str] = Field(
        None,
        max_length=1_800_000,
        description="HTTP(S) URL or data:image… URL for the case photo (max ~1.3MB)",
    )
    status: PersonStatus = "active"
    police_report_number: Optional[str] = Field(None, max_length=100)
    contact_email: Optional[EmailStr] = None
    last_seen_time: Optional[str] = Field(None, max_length=20)
    # Optional original listing (community-provided — does NOT set Verified badge)
    source_listing_url: Optional[str] = Field(None, max_length=2000)
    source_agency_name: Optional[str] = Field(None, max_length=200)
    external_case_number: Optional[str] = Field(None, max_length=100)
    source_last_checked_at: Optional[date] = None

    @field_validator("source_listing_url")
    @classmethod
    def _http_source_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not str(v).strip():
            return None
        s = str(v).strip()
        low = s.lower()
        if not (low.startswith("http://") or low.startswith("https://")):
            raise ValueError("source_listing_url must be an http(s) URL")
        return s


class PersonOut(BaseModel):
    """Serialized person row returned by the API."""

    id: UUID
    name: str
    age: int
    gender: Optional[str] = None
    last_seen_location: str
    last_seen_date: date
    description: str
    photo_url: Optional[str] = None
    status: PersonStatus
    police_report_number: Optional[str] = None
    created_at: datetime
    ai_summary: Optional[str] = None
    ai_summary_updated_at: Optional[datetime] = None
    verified_police_report: Optional[bool] = None
    last_verified_at: Optional[datetime] = None
    found_at: Optional[datetime] = None
    found_message: Optional[str] = None
    found_date: Optional[datetime] = None
    found_notes: Optional[str] = None
    verified_by: Optional[str] = None
    watchers_count: Optional[int] = None
    shares_count: Optional[int] = None
    tips_count: Optional[int] = None
    suspicious_flags: Optional[int] = None
    under_review: Optional[bool] = None
    contact_email: Optional[str] = None
    last_seen_time: Optional[str] = None
    source_listing_url: Optional[str] = None
    source_agency_name: Optional[str] = None
    external_case_number: Optional[str] = None
    source_last_checked_at: Optional[date] = None
    # Only returned on POST /persons — never on public list/get
    owner_token: Optional[str] = None


class PersonListResponse(BaseModel):
    """Wrapper for GET /persons so clients always get a stable shape."""

    count: int
    persons: List[PersonOut]


# ---------------------------------------------------------------------------
# Sightings
# ---------------------------------------------------------------------------

class SightingCreate(BaseModel):
    """Body for POST /persons/{id}/sightings — submit a public tip."""

    location_lat: float = Field(..., ge=-90, le=90, examples=[39.2904])
    location_lng: float = Field(..., ge=-180, le=180, examples=[-76.6122])
    date_time: datetime = Field(..., examples=["2026-03-05T14:30:00Z"])
    description: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        examples=["Saw someone matching the description near the waterfront."],
    )
    confidence_level: int = Field(3, ge=1, le=5, examples=[4])
    submitter_email: Optional[EmailStr] = Field(None, examples=["tipster@example.com"])
    tip_type: Optional[str] = Field(None, max_length=64, examples=["saw_person"])


class SightingOut(BaseModel):
    """Serialized sighting row returned by the API."""

    id: UUID
    person_id: UUID
    location_lat: float
    location_lng: float
    date_time: datetime
    description: str
    confidence_level: int
    created_at: datetime
    tip_type: Optional[str] = None
    # Optional intelligence fields (migration 002) — separate from confidence_level
    credibility_score: Optional[int] = Field(None, ge=1, le=10)
    family_review_flag: Optional[bool] = None
    credibility_reasons: Optional[str] = None


class SightingListResponse(BaseModel):
    """Wrapper for GET /persons/{id}/sightings."""

    count: int
    sightings: List[SightingOut]


# ---------------------------------------------------------------------------
# Natural-language search (Gemini)
# ---------------------------------------------------------------------------

class NaturalSearchRequest(BaseModel):
    """Body for POST /search/natural."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        examples=["missing women in Baltimore around age 30"],
    )


class NaturalSearchFilters(BaseModel):
    """
    Structured filters produced by Gemini from a natural-language query.

    All fields are optional — only filters the model could infer are set.
    age_min / age_max together form the age_range filter.
    """

    name: Optional[str] = None
    location: Optional[str] = None
    age_min: Optional[int] = Field(None, ge=0, le=150)
    age_max: Optional[int] = Field(None, ge=0, le=150)
    status: Optional[PersonStatus] = "active"
    gender: Optional[str] = None

    @field_validator("age_max")
    @classmethod
    def age_max_gte_min(cls, v: Optional[int], info) -> Optional[int]:
        """Ensure age_max is not less than age_min when both are present."""
        age_min = info.data.get("age_min")
        if v is not None and age_min is not None and v < age_min:
            raise ValueError("age_max must be >= age_min")
        return v


class NaturalSearchResponse(BaseModel):
    """Result of a Gemini-powered natural language search."""

    query: str
    filters: NaturalSearchFilters
    count: int
    persons: List[PersonOut]
