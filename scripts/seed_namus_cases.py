"""Seed FindMyPal with NamUs-style public case basics (no scraped photos).

Usage (API must be up against SpacetimeDB):
  cd backend
  .venv\\Scripts\\python.exe ..\\scripts\\seed_namus_cases.py
"""
from __future__ import annotations

from datetime import date, datetime

import httpx

API = "http://127.0.0.1:8000"

# (mp_id, missing_mmddyyyy, updated_mmddyyyy, last, first, age, city, state, gender)
RAW = """
MP162875|06/22/2026|09/18/2026|Lleshi|Abra|36|Anchorage|AK|Female
MP162868|07/04/2026|09/18/2026|Koyukuk|Claudia|16|Fairbanks|AK|Female
MP162669|02/24/2026|09/18/2026|Jett|Todd|55|Austin|TX|Male
MP162613|06/11/2026|09/18/2026|Wilson|Justin|41|Plano|TX|Male
MP159503|04/17/2026|09/18/2026|Abercrombie|Tabatha|37|Plano|TX|Female
MP162577|03/01/2026|09/18/2026|Noralis|Claude|43|Dallas|TX|Male
MP162561|07/23/2026|09/18/2026|Davis|Carrie|40|Knoxville|TN|Female
MP162555|08/27/2026|09/18/2026|Hunt|Malik|17|North Little Rock|AR|Male
MP162544|09/07/2026|09/18/2026|Bazarow|Emma|13|Jacksonville|AR|Female
MP162522|04/27/2026|09/18/2026|Simpson|David|64|Dallas|TX|Male
MP162521|04/24/2026|09/18/2026|Johnson|Zadre|33|Dallas|TX|Male
MP148408|12/01/2020|09/18/2026|Franklin|Marcel|34|Los Angeles|CA|Male
MP162776|01/31/2012|09/19/2026|Billings|Kayla|29|Chambersburg|PA|Female
MP162860|09/09/2017|09/18/2026|Evans|Douglas|69|Duvall|WA|Male
MP162616|12/05/2025|09/17/2026|Kelley|James|36|Kihei|HI|Male
MP162870|07/03/2026|09/17/2026|Dau-Adrian|Anthony|45|Anchorage|AK|Male
MP162791|07/20/2026|09/17/2026|Aispuro Reyes|Arturo|37|Delano|CA|Male
MP162854|09/04/2026|09/17/2026|Gonzalez|Ana|16|Phoenix|AZ|Female
MP162656|08/10/2026|09/18/2026|Sassack|Jayden|17|Island Lake|IL|Male
MP162803|09/08/2026|09/18/2026|Hopp|Keshean|17|Midland|MI|Male
MP162848|06/14/2026|09/17/2026|Gutierrez|Chris|49|Anchorage|AK|Male
MP162833|07/25/2026|09/17/2026|Pruitt|Abigail|47|Seward|AK|Female
MP162627|07/25/2026|09/16/2026|Harris|James|55|Maple Falls|WA|Male
MP162849|07/28/2026|09/16/2026|Peters|Alphonsus|69|Nulato|AK|Male
MP162814|06/29/2026|09/16/2026|Furbush|Brandon|34|Anchorage|AK|Male
""".strip().splitlines()


def parse_mdy(s: str) -> date:
    return datetime.strptime(s.strip(), "%m/%d/%Y").date()


def build_payload(row: str) -> dict:
    mp, missing, _updated, last, first, age, city, state, gender = row.split("|")
    numeric = mp.replace("MP", "").strip()
    name = f"{first.strip()} {last.strip()}"
    loc = f"{city.strip()}, {state.strip()}"
    missing_d = parse_mdy(missing)
    desc = (
        f"Public NamUs missing-person listing ({mp}). "
        f"Last known location reported as {loc}. "
        f"Date missing / last seen: {missing_d.isoformat()}. "
        "Physical description not imported — see the original NamUs case for details."
    )
    return {
        "name": name,
        "age": int(age),
        "gender": gender.strip().lower(),
        "last_seen_location": loc,
        "last_seen_date": missing_d.isoformat(),
        "description": desc,
        "photo_url": None,
        "status": "active",
        "external_case_number": mp,
        "source_agency_name": "NamUs",
        "source_listing_url": f"https://www.namus.gov/MissingPersons/Case#/{numeric}",
        "source_last_checked_at": date.today().isoformat(),
    }


def main() -> None:
    with httpx.Client(timeout=60) as client:
        health = client.get(f"{API}/health/database")
        health.raise_for_status()
        existing = client.get(f"{API}/persons", params={"status": "all"}).json()
        persons = existing.get("persons") or []
        have = {
            (p.get("external_case_number") or "").upper()
            for p in persons
            if p.get("external_case_number")
        }
        # Also skip exact name+location matches to avoid dupes without external id
        name_loc = {
            ((p.get("name") or "").lower(), (p.get("last_seen_location") or "").lower())
            for p in persons
        }

        created = skipped = failed = 0
        for line in RAW:
            if not line.strip():
                continue
            payload = build_payload(line)
            mp = payload["external_case_number"].upper()
            key = (payload["name"].lower(), payload["last_seen_location"].lower())
            if mp in have or key in name_loc:
                print(f"skip {mp} (already present)")
                skipped += 1
                continue
            r = client.post(f"{API}/persons", json=payload)
            if r.status_code in (200, 201):
                body = r.json()
                print(f"ok  {mp} -> {body.get('id')}  {payload['name']}")
                created += 1
                have.add(mp)
                name_loc.add(key)
            else:
                print(f"fail {mp} {r.status_code} {r.text[:200]}")
                failed += 1

        print(f"\ndone: created={created} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    main()
