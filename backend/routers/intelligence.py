"""
Face match + AI intelligence routes.

POST /faces/match              — compare upload to active case photos
POST /persons/check-duplicates — name + photo duplicate screening
GET  /persons/{id}/summary     — AI case summarizer
POST /persons/{id}/summary/refresh
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from services.face_match import match_probe_against_active_cases
from services.intelligence import find_duplicate_candidates, generate_case_summary

router = APIRouter(tags=["intelligence"])


class FaceMatchRequest(BaseModel):
    photo: str = Field(..., description="Base64 or data-URL image")
    min_similarity: float = Field(55.0, ge=0, le=100)


class DuplicateCheckRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    age: Optional[int] = Field(None, ge=0, le=150)
    photo: Optional[str] = None
    photo_url: Optional[str] = None


@router.post("/faces/match", summary="Match uploaded face against active cases")
def faces_match(payload: FaceMatchRequest) -> Dict[str, Any]:
    try:
        return match_probe_against_active_cases(
            payload.photo,
            min_similarity=payload.min_similarity,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/persons/check-duplicates", summary="Screen a new profile for possible duplicates")
def check_duplicates(payload: DuplicateCheckRequest) -> Dict[str, Any]:
    return find_duplicate_candidates(
        name=payload.name,
        photo_b64=payload.photo,
        photo_url=payload.photo_url,
        age=payload.age,
    )


@router.get("/persons/{person_id}/summary", summary="AI case summary")
def get_case_summary(person_id: UUID) -> Dict[str, Any]:
    try:
        return generate_case_summary(str(person_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/persons/{person_id}/summary/refresh", summary="Regenerate AI case summary")
def refresh_case_summary(person_id: UUID) -> Dict[str, Any]:
    try:
        return generate_case_summary(str(person_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
