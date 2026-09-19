"""
Geocoding helpers — browsers cannot call OSM Nominatim reliably (CORS/UA).

Uses Open-Meteo (primary) + Photon (landmarks) + Nominatim (last resort),
with in-memory cache and rate-limit backoff so Lookup heatmaps keep working
when Nominatim returns 429.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "FindMyPal/1.0 (hackathon; contact: mock@findmypal.local)"

# Process-local cache (query → result | None sentinel for misses)
_CACHE: Dict[str, Optional[Dict[str, Any]]] = {}
_LAST_NOMINATIM = 0.0

# Common demo / DC-metro anchors so Lookup still plots under provider rate limits
_STATIC: Dict[str, Dict[str, float]] = {
    "baltimore": {"lat": 39.2904, "lng": -76.6122},
    "baltimore, md": {"lat": 39.2904, "lng": -76.6122},
    "baltimore, maryland": {"lat": 39.2904, "lng": -76.6122},
    "arlington": {"lat": 38.8816, "lng": -77.0910},
    "arlington, va": {"lat": 38.8816, "lng": -77.0910},
    "arlington, virginia": {"lat": 38.8816, "lng": -77.0910},
    "crystal city": {"lat": 38.8577, "lng": -77.0519},
    "crystal city arlington": {"lat": 38.8577, "lng": -77.0519},
    "pentagon": {"lat": 38.8719, "lng": -77.0563},
    "pentagon metro": {"lat": 38.8691, "lng": -77.0540},
    "pentagon metro station": {"lat": 38.8691, "lng": -77.0540},
    "washington": {"lat": 38.9072, "lng": -77.0369},
    "washington, dc": {"lat": 38.9072, "lng": -77.0369},
    "washington dc": {"lat": 38.9072, "lng": -77.0369},
    "alexandria": {"lat": 38.8048, "lng": -77.0469},
    "alexandria, va": {"lat": 38.8048, "lng": -77.0469},
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _candidates(query: str) -> list[str]:
    q = (query or "").strip().rstrip(",").strip()
    out: list[str] = []

    def add(s: str) -> None:
        s = re.sub(r"\s+", " ", (s or "").strip(" ,"))
        if s and s not in out:
            out.append(s)

    add(q)
    add(re.sub(r"\bin\b", ",", q, flags=re.I))
    add(re.sub(r"\s+station\b", "", q, flags=re.I))
    # Landmark + city/state from commas
    parts = [p.strip() for p in re.split(r"[,]", re.sub(r"\bin\b", ",", q, flags=re.I)) if p.strip()]
    if parts:
        head = re.sub(r"\s+(station|near|area|exit|metro)\b", "", parts[0], flags=re.I).strip()
        if len(parts) >= 2:
            add(f"{head}, {parts[-1]}")
            add(", ".join(parts[-2:]))
            add(parts[-1])
        add(head)
    # Cap — do not hammer providers
    return out[:5]


def _static_hit(query: str) -> Optional[Dict[str, Any]]:
    n = _norm(query)
    if n in _STATIC:
        c = _STATIC[n]
        return {"lat": c["lat"], "lng": c["lng"], "label": query, "matched_query": n, "provider": "static"}
    # Prefer longest substring match so "Pentagon Metro… Arlington" → pentagon, not arlington
    best_key = None
    for key in _STATIC:
        if key in n or n in key:
            if best_key is None or len(key) > len(best_key):
                best_key = key
    if best_key:
        c = _STATIC[best_key]
        return {
            "lat": c["lat"],
            "lng": c["lng"],
            "label": query,
            "matched_query": best_key,
            "provider": "static",
        }
    return None


def _open_meteo(client: httpx.Client, name: str) -> Optional[Dict[str, Any]]:
    # Open-Meteo prefers place names; strip landmark noise
    cleaned = re.sub(r"\b(station|metro|near|area|exit)\b", "", name, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
    if len(cleaned) < 2:
        return None
    resp = client.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": cleaned, "count": 1, "language": "en", "format": "json"},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    if resp.status_code != 200:
        return None
    results = (resp.json() or {}).get("results") or []
    if not results:
        return None
    hit = results[0]
    return {
        "lat": float(hit["latitude"]),
        "lng": float(hit["longitude"]),
        "label": name,
        "display_name": hit.get("name"),
        "matched_query": cleaned,
        "provider": "open-meteo",
    }


def _photon(client: httpx.Client, name: str) -> Optional[Dict[str, Any]]:
    resp = client.get(
        "https://photon.komoot.io/api/",
        params={"q": name, "limit": 1},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    if resp.status_code != 200:
        return None
    features = (resp.json() or {}).get("features") or []
    if not features:
        return None
    coords = features[0].get("geometry", {}).get("coordinates") or []
    if len(coords) < 2:
        return None
    props = features[0].get("properties") or {}
    return {
        "lat": float(coords[1]),
        "lng": float(coords[0]),
        "label": name,
        "display_name": props.get("name") or props.get("city"),
        "matched_query": name,
        "provider": "photon",
    }


def _nominatim(client: httpx.Client, name: str) -> Optional[Dict[str, Any]]:
    global _LAST_NOMINATIM
    # Respect ~1 req/sec
    wait = 1.05 - (time.monotonic() - _LAST_NOMINATIM)
    if wait > 0:
        time.sleep(wait)
    _LAST_NOMINATIM = time.monotonic()
    resp = client.get(
        "https://nominatim.openstreetmap.org/search",
        params={"format": "json", "limit": 1, "q": name},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    if resp.status_code == 429:
        logger.warning("Nominatim 429 for %r — skipping", name)
        time.sleep(2.0)
        return None
    if resp.status_code != 200:
        return None
    data = resp.json()
    if not data:
        return None
    return {
        "lat": float(data[0]["lat"]),
        "lng": float(data[0]["lon"]),
        "label": name,
        "display_name": data[0].get("display_name"),
        "matched_query": name,
        "provider": "nominatim",
    }


def geocode_query(query: str) -> Optional[Dict[str, Any]]:
    q = (query or "").strip().rstrip(",").strip()
    if not q:
        return None

    cache_key = _norm(q)
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    # Fast path for known demo places
    static = _static_hit(q)
    if static:
        _CACHE[cache_key] = static
        return static

    try:
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            cands = _candidates(q)
            for candidate in cands:
                static = _static_hit(candidate)
                if static:
                    static = {**static, "label": q}
                    _CACHE[cache_key] = static
                    return static

            # Open-Meteo first across all candidates (reliable for city/region)
            for candidate in cands:
                try:
                    hit = _open_meteo(client, candidate)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("open-meteo failed for %r: %s", candidate, exc)
                    hit = None
                if hit:
                    hit["label"] = q
                    _CACHE[cache_key] = hit
                    return hit

            # Photon for landmarks / fuller phrases
            for candidate in cands:
                try:
                    hit = _photon(client, candidate)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("photon failed for %r: %s", candidate, exc)
                    hit = None
                if hit:
                    hit["label"] = q
                    _CACHE[cache_key] = hit
                    return hit

            # Nominatim last (often rate-limited)
            for candidate in cands[:2]:
                try:
                    hit = _nominatim(client, candidate)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("nominatim failed for %r: %s", candidate, exc)
                    hit = None
                if hit:
                    hit["label"] = q
                    _CACHE[cache_key] = hit
                    return hit
    except Exception as exc:  # noqa: BLE001
        logger.warning("Geocode failed for %r: %s", q, exc)
        _CACHE[cache_key] = None
        return None

    _CACHE[cache_key] = None
    return None
