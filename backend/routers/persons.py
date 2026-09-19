"""
Person routes for FindMyPal.

POST   /persons              — create a missing-person profile
GET    /persons              — list / filter profiles
GET    /persons/{person_id}  — single profile
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from database import get_supabase
from schemas import PersonCreate, PersonListResponse, PersonOut
from services.owner_auth import issue_owner_token, remember_token
from services.advanced import notify_zip_alerts_for_new_case, queue_email

router = APIRouter(tags=["persons"])


def _escape_ilike(term: str) -> str:
    return (term or "").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _row_to_person(row: dict, *, include_owner_token: bool = False, public: bool = True) -> PersonOut:
    allowed = set(PersonOut.model_fields.keys())
    cleaned = {k: v for k, v in row.items() if k in allowed}
    if public:
        cleaned["owner_token"] = None
        cleaned["contact_email"] = None
    if not include_owner_token:
        cleaned["owner_token"] = None
    return PersonOut(**cleaned)


def _strip_list_photo(row: dict) -> dict:
    out = dict(row)
    url = out.get("photo_url") or ""
    if isinstance(url, str) and url.startswith("data:"):
        out["photo_url"] = None
    out["owner_token"] = None
    out["contact_email"] = None
    return out


@router.post(
    "/persons",
    response_model=PersonOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a missing-person profile",
)
def create_person(payload: PersonCreate) -> PersonOut:
    supabase = get_supabase()
    data = payload.model_dump(mode="json")
    data["status"] = "active"
    token = issue_owner_token()
    data["owner_token"] = token
    if (data.get("police_report_number") or "").strip():
        data["verified_police_report"] = True
        data["last_verified_at"] = datetime.now(timezone.utc).isoformat()

    result = None
    try:
        result = supabase.table("persons").insert(data).execute()
    except Exception:
        data.pop("owner_token", None)
        data.pop("contact_email", None)
        data.pop("last_seen_time", None)
        data.pop("verified_police_report", None)
        result = supabase.table("persons").insert(data).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create person profile",
        )

    row = dict(result.data[0])
    pid = str(row["id"])
    remember_token(pid, token)
    row["owner_token"] = token

    try:
        notify_zip_alerts_for_new_case(row)
    except Exception:
        pass

    contact = (payload.contact_email and str(payload.contact_email)) or None
    if contact:
        try:
            supabase.table("alert_subscriptions").insert(
                {
                    "kind": "case_watch",
                    "email": contact,
                    "person_id": pid,
                    "active": True,
                }
            ).execute()
            queue_email(
                contact,
                "FindMyPal — you are watching this case",
                f"You will get logged alerts for case updates on {payload.name}. "
                "Delivery is logged on the server unless SMTP is configured.",
                kind="watch_confirm",
                meta={"person_id": pid},
            )
        except Exception:
            pass

    return _row_to_person(row, include_owner_token=True, public=False)


@router.get(
    "/persons",
    response_model=PersonListResponse,
    summary="List missing-person profiles with optional filters",
)
def list_persons(
    name: Optional[str] = Query(None, description="Case-insensitive partial match on name"),
    location: Optional[str] = Query(None, description="Case-insensitive partial match on last_seen_location"),
    q: Optional[str] = Query(None, description="Match name OR last_seen_location"),
    age_min: Optional[int] = Query(None, ge=0, le=150),
    age_max: Optional[int] = Query(None, ge=0, le=150),
    status_filter: Optional[str] = Query("active", alias="status"),
) -> PersonListResponse:
    if age_min is not None and age_max is not None and age_max < age_min:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="age_max must be greater than or equal to age_min",
        )

    supabase = get_supabase()
    query = supabase.table("persons").select("*")

    if q:
        safe = _escape_ilike(q)
        query = query.or_(f"name.ilike.*{safe}*,last_seen_location.ilike.*{safe}*")
    else:
        if name:
            query = query.ilike("name", f"%{_escape_ilike(name)}%")
        if location:
            query = query.ilike("last_seen_location", f"%{_escape_ilike(location)}%")

    if age_min is not None:
        query = query.gte("age", age_min)
    if age_max is not None:
        query = query.lte("age", age_max)
    if status_filter and status_filter.lower() != "all":
        query = query.eq("status", status_filter.lower())

    query = query.order("created_at", desc=True)
    result = query.execute()
    rows = result.data or []
    persons = [_row_to_person(_strip_list_photo(row)) for row in rows]
    return PersonListResponse(count=len(persons), persons=persons)


@router.get(
    "/persons/{person_id}",
    response_model=PersonOut,
    summary="Get a single missing-person profile",
)
def get_person(person_id: UUID) -> PersonOut:
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
    return _row_to_person(result.data[0], public=True)
