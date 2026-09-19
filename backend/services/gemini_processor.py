"""
Smart Person Search — Gemini extraction + Nominatim geocoding.

Takes raw public-web snippets and returns structured sighting mentions,
then geocodes any location strings for the Leaflet heatmap.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

import google.generativeai as genai
import httpx

from config import get_settings

logger = logging.getLogger(__name__)

USER_AGENT = "FindMyPalLookup/1.0 (missing-persons research; contact: mock@findmypal.local)"

SYSTEM_PROMPT_TEMPLATE = """
You are analyzing public mentions of a missing person named {name}.
Below are raw text snippets from various public sources.

Extract ONLY mentions that contain at least one of:
- A location (city, neighborhood, street, landmark)
- A time or date reference
- A physical description matching the person

For each valid mention return JSON:
{{
  "source": "platform name",
  "date": "date if mentioned",
  "location": "location if mentioned",
  "quote": "exact relevant quote under 100 words",
  "confidence": "high/medium/low",
  "url": "source url"
}}

Ignore irrelevant mentions, spam, and unrelated people with the same name.
Return only a JSON array. Nothing else.
""".strip()


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    """Parse a JSON array from a Gemini response (handles fences)."""
    cleaned = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.I)
    if fence:
        cleaned = fence.group(1).strip()
    if not cleaned.startswith("["):
        match = re.search(r"\[[\s\S]*\]", cleaned)
        if match:
            cleaned = match.group(0)
    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array from Gemini")
    return [item for item in data if isinstance(item, dict)]


def _heuristic_extract(name: str, raw_mentions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fallback extractor when Gemini is unavailable.

    Keeps snippets that mention the name plus location/time-ish language.
    """
    location_words = re.compile(
        r"\b(in|near|around|at|from)\s+[A-Z][A-Za-z0-9 .'-]{2,40}",
    )
    time_words = re.compile(
        r"\b(yesterday|today|last\s+night|last\s+week|monday|tuesday|wednesday|"
        r"thursday|friday|saturday|sunday|january|february|march|april|may|june|"
        r"july|august|september|october|november|december|\d{1,2}/\d{1,2}/\d{2,4}|"
        r"20\d{2})\b",
        re.I,
    )
    name_l = name.lower()
    out: List[Dict[str, Any]] = []
    for item in raw_mentions:
        text = item.get("text") or item.get("snippet") or ""
        if name_l not in text.lower() and name_l not in (item.get("title") or "").lower():
            # Still keep if title/snippet is short search-result style
            if name.split()[0].lower() not in text.lower():
                continue
        has_loc = bool(location_words.search(text)) or bool(item.get("date"))
        has_time = bool(time_words.search(text)) or bool(item.get("date"))
        if not (has_loc or has_time):
            # Keep a few high-signal social/news hits anyway
            if item.get("source") not in {"news", "reddit", "x", "youtube"}:
                continue
        loc_match = location_words.search(text)
        out.append(
            {
                "source": item.get("source") or "web",
                "date": item.get("date") or "",
                "location": loc_match.group(0)[3:].strip() if loc_match else "",
                "quote": (text or item.get("title") or "")[:400],
                "confidence": "medium" if (has_loc and has_time) else "low",
                "url": item.get("url") or "",
            }
        )
        if len(out) >= 40:
            break
    return out


def extract_sightings_with_gemini(name: str, raw_mentions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Send raw mentions to Gemini and return structured sighting JSON objects.
    Falls back to heuristic extraction if Gemini is not configured / fails.
    """
    settings = get_settings()
    if not raw_mentions:
        return []

    # Cap payload size for the model
    payload = []
    for item in raw_mentions[:60]:
        payload.append(
            {
                "source": item.get("source"),
                "date": item.get("date"),
                "url": item.get("url"),
                "text": (item.get("text") or item.get("snippet") or "")[:600],
            }
        )

    key = settings.gemini_api_key
    if not key or key.upper().startswith("YOUR_"):
        logger.info("Gemini not configured — using heuristic extractor")
        return _heuristic_extract(name, raw_mentions)

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT_TEMPLATE.format(name=name),
        )
        prompt = (
            f"Person name: {name}\n\n"
            f"Raw mentions JSON:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        )
        text = getattr(response, "text", "") or ""
        mentions = _extract_json_array(text)
        cleaned: List[Dict[str, Any]] = []
        for m in mentions:
            conf = str(m.get("confidence") or "low").lower()
            if conf not in {"high", "medium", "low"}:
                conf = "low"
            cleaned.append(
                {
                    "source": str(m.get("source") or "web")[:60],
                    "date": str(m.get("date") or "")[:40],
                    "location": str(m.get("location") or "")[:120],
                    "quote": str(m.get("quote") or "")[:500],
                    "confidence": conf,
                    "url": str(m.get("url") or "")[:500],
                }
            )
        return cleaned
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini extraction failed (%s) — heuristic fallback", exc)
        return _heuristic_extract(name, raw_mentions)


async def geocode_location(client: httpx.AsyncClient, location: str) -> Optional[Dict[str, float]]:
    """Geocode a free-text location with OpenStreetMap Nominatim."""
    if not location or len(location.strip()) < 2:
        return None
    try:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": location, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data:
            return None
        return {
            "lat": float(data[0]["lat"]),
            "lng": float(data[0]["lon"]),
            "label": location,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Geocode failed for %r: %s", location, exc)
        return None


async def geocode_mentions(sightings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Geocode unique location strings from sightings.
    Returns list of {lat, lng, label, count} for the heatmap.
    """
    counts: Counter = Counter()
    for s in sightings:
        loc = (s.get("location") or "").strip()
        if loc:
            counts[loc] += 1

    if not counts:
        return []

    locations: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=20.0) as client:
        # Nominatim usage policy: sequential with a small delay is safer;
        # for hackathon speed we gather but cap unique places.
        unique = list(counts.keys())[:25]

        async def _one(label: str):
            coords = await geocode_location(client, label)
            if not coords:
                return None
            return {
                "lat": coords["lat"],
                "lng": coords["lng"],
                "label": label,
                "count": counts[label],
            }

        import asyncio

        # Mild sequential batches of 5 to be polite to Nominatim
        for i in range(0, len(unique), 5):
            batch = unique[i : i + 5]
            got = await asyncio.gather(*[_one(label) for label in batch])
            for item in got:
                if item:
                    locations.append(item)
            await asyncio.sleep(1.0)

    return locations


def build_summary(
    name: str,
    photo_data_url: Optional[str],
    sightings: List[Dict[str, Any]],
    locations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Assemble the SUMMARY block for the report."""
    dates = [s.get("date") for s in sightings if s.get("date")]
    dates_sorted = sorted(dates)
    top_location = ""
    if locations:
        top_location = max(locations, key=lambda x: x.get("count", 0)).get("label", "")
    elif sightings:
        loc_counts = Counter(
            (s.get("location") or "").strip() for s in sightings if (s.get("location") or "").strip()
        )
        if loc_counts:
            top_location = loc_counts.most_common(1)[0][0]

    return {
        "name": name,
        "photo_data_url": photo_data_url,  # session-only; never written to disk
        "total_mentions": len(sightings),
        "date_range": {
            "start": dates_sorted[0] if dates_sorted else None,
            "end": dates_sorted[-1] if dates_sorted else None,
        },
        "most_frequent_location": top_location or None,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def sort_sightings_chronologically(sightings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort by date string when possible; undated items go last."""

    def key(item: Dict[str, Any]):
        d = item.get("date") or ""
        return (0, d) if d else (1, "")

    return sorted(sightings, key=key)
