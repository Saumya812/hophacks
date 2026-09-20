"""Create one Baltimore demo case with tip coords for CitiWatch nearest-camera checks."""
from __future__ import annotations

import httpx

API = "http://127.0.0.1:8000"
DEMO_TAG = "DEMO-BALT-001"


def main() -> None:
    payload = {
        "name": "Jordan Blake",
        "age": 24,
        "gender": "male",
        "last_seen_location": "Inner Harbor, Baltimore, MD",
        "last_seen_date": "2026-09-15",
        "description": (
            "Demo Baltimore case for CitiWatch nearest-camera testing. "
            "Approx 5'10\", short dark hair, last seen near the Inner Harbor promenade "
            "wearing a navy hoodie and jeans. Not a real missing person — "
            "FindMyPal hackathon demo only."
        ),
        "photo_url": None,
        "status": "active",
        "external_case_number": DEMO_TAG,
        "source_agency_name": "FindMyPal Demo",
        "source_listing_url": "https://findmypal.app/demo/baltimore",
        "source_last_checked_at": "2026-09-19",
    }
    tips = [
        {
            "location_lat": 39.2858,
            "location_lng": -76.6131,
            "date_time": "2026-09-15T18:30:00Z",
            "description": "[Demo tip] Possible sighting near Inner Harbor amphitheater, navy hoodie.",
            "confidence_level": 4,
            "tip_type": "saw_person",
        },
        {
            "location_lat": 39.2904,
            "location_lng": -76.6122,
            "date_time": "2026-09-16T14:00:00Z",
            "description": "[Demo tip] Someone matching description walking toward City Hall / downtown.",
            "confidence_level": 3,
            "tip_type": "have_info",
        },
        {
            "location_lat": 39.2830,
            "location_lng": -76.6085,
            "date_time": "2026-09-17T20:15:00Z",
            "description": "[Demo tip] Brief sighting near Fells Point waterfront area.",
            "confidence_level": 2,
            "tip_type": "unsure",
        },
    ]

    with httpx.Client(timeout=90) as client:
        health = client.get(f"{API}/health/database")
        health.raise_for_status()

        persons = client.get(f"{API}/persons", params={"status": "all"}).json().get("persons") or []
        pid = None
        for p in persons:
            if (p.get("external_case_number") or "") == DEMO_TAG or (p.get("name") or "").lower() == "jordan blake":
                pid = p["id"]
                print(f"exists {pid} {p['name']}")
                break
        if not pid:
            r = client.post(f"{API}/persons", json=payload)
            r.raise_for_status()
            body = r.json()
            pid = body["id"]
            print(f"created {pid} {body['name']}")

        existing = client.get(f"{API}/persons/{pid}/sightings").json().get("sightings") or []
        if len(existing) >= 3:
            print(f"tips already present ({len(existing)})")
        else:
            for tip in tips:
                r = client.post(f"{API}/persons/{pid}/sightings", json=tip)
                print(f"tip {r.status_code} {tip['location_lat']},{tip['location_lng']}")
                r.raise_for_status()

        nearest = client.get(
            f"{API}/analytics/baltimore/nearest/{pid}",
            params={"k": 3, "max_m": 2500},
        )
        nearest.raise_for_status()
        data = nearest.json()
        print("camera_catalog", data.get("camera_catalog_count"))
        print("tips_with_cameras", data.get("tips_with_cameras"))
        last_seen = data.get("last_seen") or {}
        cams = last_seen.get("nearest_cameras") or []
        print("last_seen_cams", len(cams))
        for cam in cams[:3]:
            print(" ", cam.get("distance_label"), cam.get("location") or cam.get("cam_number"))
        for tip in data.get("tips") or []:
            tc = tip.get("nearest_cameras") or []
            print(f"tip @{tip.get('lat')},{tip.get('lng')} -> {len(tc)} cameras")
            for cam in tc[:2]:
                print(" ", cam.get("distance_label"), cam.get("location") or cam.get("cam_number"))

        print(f"PROFILE http://localhost:5174/person/{pid}")
        print(f"MISSING http://localhost:5174/report-missing")


if __name__ == "__main__":
    main()
