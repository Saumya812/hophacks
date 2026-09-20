"""Attach cropped portraits from PDF screenshots to Spacetime person rows."""
from __future__ import annotations

import base64
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from PIL import Image

from config import get_settings
from database import get_database

ASSETS = Path(
    r"C:\Users\User\.cursor\projects\c-Projects-FindMyPal-hophacks\assets"
)

# Exact filenames from the chat attachment list → person name in DB
MAP = [
    ("c5cd9f79-890f-45ac-808c-2e0041fcce66", "Emma Bazarow"),
    ("084b0bde-c3ad-4eb8-bce3-04627f835c3b", "Malik Hunt"),
    ("de0d3bc1-afa1-484d-8253-91bf48e18852", "Justin Wilson"),
    ("224bc80f-037b-4cd0-ab7d-497adff1a3c4", "Todd Jett"),
    ("c298d841-c159-461f-a981-901850b0ac8c", "Abra Lleshi"),
    ("26999422-1ce5-483b-89eb-8fe36d58510a", "Brandon Furbush"),
    ("f9e0d24d-71e9-4cc2-8c11-d0c548053719", "Alphonsus Peters"),
    ("9d940dad-1fca-4d78-9b0c-b05694b8668b", "James Harris"),
    ("6420580e-19d5-4faf-b5e2-68ff1a9481f3", "Abigail Pruitt"),
    ("1819eef8-e6a8-4bb0-bf80-a3e8ba5e4965", "Chris Gutierrez"),
    ("18e14a69-c746-4015-9607-b1b72a3d40eb", "Keshean Hopp"),
    ("45dda613-be8e-4a74-a52b-d7e0ca0e9049", "Jayden Sassack"),
    ("83df23a6-7db1-41d5-9637-13d98327dec6", "Arturo Aispuro Reyes"),
    ("7b294e9e-c4f2-4ae8-821f-6ca46904ecbd", "Anthony Dau-Adrian"),
    ("61fa5116-c90a-498e-8215-263332854410", "James Kelley"),
    ("161ad86c-2395-4a63-93f2-b23b6f0ae5f2", "Douglas Evans"),
    ("e442fc41-5934-441f-bc6c-a4fc93a405e1", "Kayla Billings"),
]


def find_file(token: str) -> Path:
    matches = list(ASSETS.glob(f"*{token}*.png"))
    if not matches:
        raise FileNotFoundError(token)
    return matches[0]


def is_white(px, thresh: int = 248) -> bool:
    return px[0] >= thresh and px[1] >= thresh and px[2] >= thresh


def extract_portrait(path: Path) -> Image.Image:
    """Keep only the face photo — drop 'View case', status, name, last-seen text."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()

    # Downsample mask: photo pixels form a dense blob; UI text is sparse.
    step = max(1, min(w, h) // 120)
    gw, gh = (w + step - 1) // step, (h + step - 1) // step
    mask = [[False] * gw for _ in range(gh)]
    for gy in range(gh):
        for gx in range(gw):
            x, y = min(gx * step, w - 1), min(gy * step, h - 1)
            mask[gy][gx] = not is_white(px[x, y])

    # Connected components (4-connected); pick largest blob that looks like a photo.
    visited = [[False] * gw for _ in range(gh)]
    best = None  # (area, minx, miny, maxx, maxy)

    for sy in range(gh):
        for sx in range(gw):
            if not mask[sy][sx] or visited[sy][sx]:
                continue
            stack = [(sx, sy)]
            visited[sy][sx] = True
            minx = maxx = sx
            miny = maxy = sy
            area = 0
            while stack:
                x, y = stack.pop()
                area += 1
                if x < minx:
                    minx = x
                if x > maxx:
                    maxx = x
                if y < miny:
                    miny = y
                if y > maxy:
                    maxy = y
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if 0 <= nx < gw and 0 <= ny < gh and mask[ny][nx] and not visited[ny][nx]:
                        visited[ny][nx] = True
                        stack.append((nx, ny))

            bw = maxx - minx + 1
            bh = maxy - miny + 1
            # Skip thin text lines / single letters
            if bw < 12 or bh < 12:
                continue
            if bh < 18 and bw > bh * 3:
                continue  # horizontal text
            if bw < 18 and bh > bw * 4:
                continue  # vertical letter stroke
            fill = area / max(1, bw * bh)
            if fill < 0.25:
                continue  # sparse text glyphs
            score = area
            if best is None or score > best[0]:
                best = (score, minx, miny, maxx, maxy)

    if best is None:
        raise ValueError(f"no portrait blob in {path.name}")

    _, minx, miny, maxx, maxy = best
    # Map grid coords back to pixels; pad 1 cell then tighten
    left = max(0, minx * step - step)
    top = max(0, miny * step - step)
    right = min(w, (maxx + 1) * step + step)
    bottom = min(h, (maxy + 1) * step + step)
    portrait = im.crop((left, top, right, bottom))

    # Final white-border trim on the isolated photo
    pw, ph = portrait.size
    ppx = portrait.load()

    def col_has(x: int) -> bool:
        return any(not is_white(ppx[x, y]) for y in range(0, ph, max(1, ph // 50)))

    def row_has(y: int) -> bool:
        return any(not is_white(ppx[x, y]) for x in range(0, pw, max(1, pw // 50)))

    l2, r2, t2, b2 = 0, pw, 0, ph
    for x in range(pw):
        if col_has(x):
            l2 = x
            break
    for x in range(pw - 1, -1, -1):
        if col_has(x):
            r2 = x + 1
            break
    for y in range(ph):
        if row_has(y):
            t2 = y
            break
    for y in range(ph - 1, -1, -1):
        if row_has(y):
            b2 = y + 1
            break
    portrait = portrait.crop((l2, t2, max(l2 + 8, r2), max(t2 + 8, b2)))

    portrait.thumbnail((480, 640), Image.Resampling.LANCZOS)
    return portrait


def to_data_url(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82, optimize=True)
    raw = buf.getvalue()
    if len(raw) > 350_000:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=65, optimize=True)
        raw = buf.getvalue()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def main() -> None:
    get_settings.cache_clear()
    db = get_database()
    people = db.table("persons").select("id,name,photo_url").execute().data or []
    by_name = {(p.get("name") or "").strip().lower(): p for p in people}

    out_dir = Path(__file__).resolve().parent.parent / "frontend" / "public" / "case-photos"
    out_dir.mkdir(parents=True, exist_ok=True)

    ok = fail = 0
    for token, name in MAP:
        try:
            src = find_file(token)
            portrait = extract_portrait(src)
            data_url = to_data_url(portrait)
            # Also save a static file for debugging / optional URL use
            safe = name.lower().replace(" ", "-").replace(".", "")
            portrait.save(out_dir / f"{safe}.jpg", quality=85)

            person = by_name.get(name.lower())
            if not person:
                print(f"MISS person row: {name}")
                fail += 1
                continue

            db.table("persons").update({"photo_url": data_url}).eq(
                "id", person["id"]
            ).execute()
            print(f"OK  {name}  ({len(data_url)//1024} KB data-url) <- {src.name[-40:]}")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {name}: {exc}")
            fail += 1

    with_photo = [
        p
        for p in (db.table("persons").select("id,name,photo_url").execute().data or [])
        if p.get("photo_url")
    ]
    print(f"\ndone ok={ok} fail={fail}; persons with photo now={len(with_photo)}")
    for p in with_photo:
        print(" ", p.get("name"))


if __name__ == "__main__":
    main()
