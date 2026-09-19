"""
Baltimore CitiWatch camera listings — public locations only (not live video).
Used to suggest nearest listed cameras to tips / last-seen for official follow-up.
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

CAMERAS_URL = (
    "https://geodata.baltimorecity.gov/egis/rest/services/"
    "CityView/CitiWatchCamera/FeatureServer/0/query"
)

_CACHE: Dict[str, Any] = {"ts": 0.0, "cameras": []}
_CACHE_TTL_SEC = 45 * 60


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def fetch_cameras(limit: int = 800) -> List[Dict[str, Any]]:
    now = time.time()
    if _CACHE["cameras"] and (now - float(_CACHE["ts"])) < _CACHE_TTL_SEC:
        return list(_CACHE["cameras"])[:limit]

    r = httpx.get(
        CAMERAS_URL,
        params={
            "where": "1=1",
            "outFields": "CAM_NUMBER,CAM_LOCATION",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
            "resultRecordCount": str(min(max(limit, 1), 2000)),
        },
        timeout=45,
        follow_redirects=True,
        headers={"User-Agent": "FindMyPal-API/1.0"},
    )
    r.raise_for_status()
    payload = r.json()
    cameras: List[Dict[str, Any]] = []
    for feat in payload.get("features") or []:
        geom = feat.get("geometry") or {}
        attrs = feat.get("attributes") or {}
        lon, lat = geom.get("x"), geom.get("y")
        if lat is None or lon is None:
            continue
        cameras.append(
            {
                "cam_number": attrs.get("CAM_NUMBER"),
                "location": attrs.get("CAM_LOCATION") or "CitiWatch camera",
                "lat": float(lat),
                "lng": float(lon),
            }
        )
    _CACHE["cameras"] = cameras
    _CACHE["ts"] = now
    return list(cameras)[:limit]


def nearest_to_point(
    lat: float,
    lng: float,
    cameras: List[Dict[str, Any]],
    k: int = 3,
    max_m: float = 2500.0,
) -> List[Dict[str, Any]]:
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for cam in cameras:
        d = haversine_m(lat, lng, float(cam["lat"]), float(cam["lng"]))
        if d <= max_m:
            scored.append((d, cam))
    scored.sort(key=lambda x: x[0])
    out = []
    for d, cam in scored[:k]:
        out.append(
            {
                **cam,
                "distance_m": round(d),
                "distance_label": (
                    f"{d:.0f} m" if d < 1000 else f"{d / 1000:.1f} km"
                ),
            }
        )
    return out


DISCLAIMER = (
    "These are public CitiWatch *location listings*, not live video feeds. "
    "FindMyPal cannot watch cameras or run face match on city CCTV. "
    "Distance is approximate. Ask police or the camera operator through official channels "
    "if you need footage reviewed — do not approach strangers or trespass."
)

HOW_TO_USE = [
    "Community tips appear with the nearest listed cameras by distance.",
    "Use this to know where to *request* a footage review officially — not as proof a tip is true.",
    "Face matching stays on Lookup / tip photos you upload — separate from this list.",
    "For the full city map, open Dashboard → Baltimore civic context (marimo).",
]
