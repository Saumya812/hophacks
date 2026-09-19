"""
Geocoding helpers — Nominatim via backend (browsers often get CORS / UA blocks).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "FindMyPal/1.0 (hackathon; contact: mock@findmypal.local)"


def geocode_query(query: str) -> Optional[Dict[str, Any]]:
    q = (query or "").strip().rstrip(",").strip()
    if not q:
        return None

    candidates: list[str] = [q]

    def _add(s: str) -> None:
        s = re.sub(r"\s+", " ", (s or "").strip(" ,"))
        if s and s not in candidates:
            candidates.append(s)

    # Common missing-person phrasing cleanup
    _add(re.sub(r"\bin\b", ",", q, flags=re.I))
    _add(re.sub(r"\s+station\b", "", q, flags=re.I))
    _add(re.sub(r"\s+station\b", "", re.sub(r"\bin\b", ",", q, flags=re.I), flags=re.I))
    # Keep first landmark + last two comma parts (city, state)
    parts = [p.strip() for p in re.split(r",", q) if p.strip()]
    if len(parts) >= 2:
        head = re.sub(r"\s+(station|near|area|exit)\b", "", parts[0], flags=re.I)
        head = re.sub(r"\bin\b.*$", "", head, flags=re.I).strip()
        _add(f"{head}, {parts[-1]}")
        if len(parts) >= 2:
            _add(f"{head}, {', '.join(parts[-2:])}")

    try:
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            for candidate in candidates:
                resp = client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"format": "json", "limit": 1, "q": candidate},
                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                if not data:
                    continue
                return {
                    "lat": float(data[0]["lat"]),
                    "lng": float(data[0]["lon"]),
                    "label": q,
                    "display_name": data[0].get("display_name"),
                    "matched_query": candidate,
                }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Geocode failed for %r: %s", q, exc)
        return None
    return None
