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
    photo_url: Optional[str] = Field(None, max_length=2000)
    status: PersonStatus = "active"
    police_report_number: Optional[str] = Field(None, max_length=100)


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


class SightingOut(BaseModel):
    """Serialized sighting row returned by the API."""

    id: UUID
    person_id: UUID
    location_lat: float
    location_lng: float
    date_time: datetime
    description: str
    confidence_level: int
    submitter_email: Optional[str] = None
    created_at: datetime


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
