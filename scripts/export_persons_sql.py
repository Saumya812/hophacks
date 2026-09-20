"""Export active and found persons from the live API into SQL dump files."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:8000"

COLS = [
    "id",
    "name",
    "age",
    "gender",
    "last_seen_location",
    "last_seen_date",
    "description",
    "photo_url",
    "status",
    "police_report_number",
    "created_at",
    "ai_summary",
    "ai_summary_updated_at",
    "verified_police_report",
    "last_verified_at",
    "found_at",
    "found_message",
    "watchers_count",
    "shares_count",
    "tips_count",
    "suspicious_flags",
    "under_review",
    "owner_token",
    "contact_email",
    "last_seen_time",
    "source_listing_url",
    "source_agency_name",
    "external_case_number",
    "source_last_checked_at",
    "found_date",
    "found_notes",
    "verified_by",
]


def fetch(status: str) -> list[dict]:
    with urllib.request.urlopen(f"{API}/persons?status={status}", timeout=120) as resp:
        data = json.load(resp)
    return list(data.get("persons") or [])


def sql_lit(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and value == int(value):
            return str(int(value))
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def emit(path: Path, title: str, persons: list[dict]) -> None:
    lines: list[str] = [
        "-- =============================================================================",
        f"-- FindMyPal — {title}",
        "-- Snapshot exported from live SpacetimeDB via FastAPI /persons",
        f"-- Row count: {len(persons)}",
        "-- =============================================================================",
        "",
        "CREATE TABLE IF NOT EXISTS persons_export (",
        "    id                       TEXT PRIMARY KEY,",
        "    name                     TEXT NOT NULL,",
        "    age                      INTEGER,",
        "    gender                   TEXT,",
        "    last_seen_location       TEXT,",
        "    last_seen_date           TEXT,",
        "    description              TEXT,",
        "    photo_url                TEXT,",
        "    status                   TEXT,",
        "    police_report_number     TEXT,",
        "    created_at               TEXT,",
        "    ai_summary               TEXT,",
        "    ai_summary_updated_at    TEXT,",
        "    verified_police_report   BOOLEAN,",
        "    last_verified_at         TEXT,",
        "    found_at                 TEXT,",
        "    found_message            TEXT,",
        "    watchers_count           INTEGER,",
        "    shares_count             INTEGER,",
        "    tips_count               INTEGER,",
        "    suspicious_flags         INTEGER,",
        "    under_review             BOOLEAN,",
        "    owner_token              TEXT,",
        "    contact_email            TEXT,",
        "    last_seen_time           TEXT,",
        "    source_listing_url       TEXT,",
        "    source_agency_name       TEXT,",
        "    external_case_number     TEXT,",
        "    source_last_checked_at   TEXT,",
        "    found_date               TEXT,",
        "    found_notes              TEXT,",
        "    verified_by              TEXT",
        ");",
        "",
    ]
    col_list = ", ".join(COLS)
    for index, person in enumerate(persons, start=1):
        name = person.get("name") or "?"
        status = person.get("status") or "?"
        pid = person.get("id") or "?"
        values = ", ".join(sql_lit(person.get(col)) for col in COLS)
        lines.append(f"-- {index}. {name} ({status}) id={pid}")
        lines.append(f"INSERT INTO persons_export ({col_list}) VALUES ({values});")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {path} ({path.stat().st_size} bytes, {len(persons)} rows)")


def main() -> None:
    active = sorted(fetch("active"), key=lambda row: (row.get("name") or "").lower())
    found = sorted(fetch("found"), key=lambda row: (row.get("name") or "").lower())
    emit(ROOT / "missing_people.sql", "ACTIVE / MISSING people", active)
    emit(ROOT / "found.sql", "FOUND & REUNITED people", found)


if __name__ == "__main__":
    main()
