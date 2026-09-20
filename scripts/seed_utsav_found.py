"""Add Utsav Shah as a reunited (found) demo case with the provided photo."""
from __future__ import annotations

import base64
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from PIL import Image

from config import get_settings
from database import get_database

SRC = Path(
    r"C:\Users\User\.cursor\projects\c-Projects-FindMyPal-hophacks\assets"
    r"\c__Users_User_AppData_Roaming_Cursor_User_workspaceStorage_ecbe86187d29129beb28394ce5d11b10_images_Utsav_Shah_Photograph-eee01c20-59e7-4e3d-8793-6f1780992bb4.jpg"
)


def is_white(px, thresh: int = 248) -> bool:
    return px[0] >= thresh and px[1] >= thresh and px[2] >= thresh


def load_photo(path: Path) -> tuple[Image.Image, str]:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    left, right, top, bottom = 0, w, 0, h
    for x in range(w):
        if any(not is_white(px[x, y]) for y in range(0, h, max(1, h // 60))):
            left = x
            break
    for x in range(w - 1, -1, -1):
        if any(not is_white(px[x, y]) for y in range(0, h, max(1, h // 60))):
            right = x + 1
            break
    for y in range(h):
        if any(not is_white(px[x, y]) for x in range(0, w, max(1, w // 60))):
            top = y
            break
    for y in range(h - 1, -1, -1):
        if any(not is_white(px[x, y]) for x in range(0, w, max(1, w // 60))):
            bottom = y + 1
            break
    im = im.crop((left, top, max(left + 8, right), max(top + 8, bottom)))
    im.thumbnail((480, 640), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=85, optimize=True)
    raw = buf.getvalue()
    data_url = f"data:image/jpeg;base64,{base64.b64encode(raw).decode('ascii')}"
    return im, data_url


def main() -> None:
    im, data_url = load_photo(SRC)
    out = ROOT / "frontend" / "public" / "case-photos" / "utsav-shah.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=85)

    get_settings.cache_clear()
    db = get_database()
    people = db.table("persons").select("id,name,status").execute().data or []
    existing = next(
        (p for p in people if "utsav" in (p.get("name") or "").lower()),
        None,
    )

    now = datetime.now(timezone.utc).isoformat()
    row = {
        "name": "Utsav Shah",
        "age": 22,
        "gender": "male",
        "last_seen_location": "Inner Harbor, Baltimore, MD",
        "last_seen_date": "2026-09-12",
        "description": (
            "Demo reunited case. Approx 5'9\", dark hair, short beard, last seen near "
            "the Inner Harbor promenade wearing a white t-shirt. "
            "Not a real missing person — FindMyPal hackathon demo only."
        ),
        "photo_url": data_url,
        "status": "found",
        "found_at": now,
        "found_date": now,
        "found_message": "Found safe near Inner Harbor. Reunited with family.",
        "found_notes": "Located near Inner Harbor, Baltimore; marked found for demo.",
        "verified_by": "law_enforcement",
        "external_case_number": "DEMO-FOUND-UTSAV",
        "source_agency_name": "FindMyPal Demo",
    }

    if existing:
        db.table("persons").update(row).eq("id", existing["id"]).execute()
        print(f"updated {existing['id']} {row['name']} status=found")
    else:
        res = db.table("persons").insert(row).execute()
        pid = (res.data or [{}])[0].get("id", "?")
        print(f"created {pid} {row['name']} status=found {im.size}")


if __name__ == "__main__":
    main()
