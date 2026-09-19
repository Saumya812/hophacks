"""
Smart Person Search — Gemini extraction + Nominatim geocoding.

Takes raw public-web snippets and returns structured sighting mentions,
then geocodes any location strings for the Leaflet heatmap.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from services.gemini_client import gemini_configured
from services.geocode import geocode_query

logger = logging.getLogger(__name__)

USER_AGENT = "FindMyPalLookup/1.0 (missing-persons research; contact: mock@findmypal.local)"

# Bidirectional / formatting marks that leak into scraped locale dates (e.g. 08‏/09‏/2026)
_BIDI_RE = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")


def _clean_date_text(raw: Any) -> str:
    return _BIDI_RE.sub("", str(raw or "")).strip()


def parse_mention_date(raw: Any) -> Optional[datetime]:
    """
    Parse heterogeneous mention dates into a datetime (date-only).
    Supports ISO, 'Jul 24, 2026', '08/09/2026', '2026/09/08', etc.
    """
    s = _clean_date_text(raw)
    if not s or s.lower() in {"—", "-", "n/a", "unknown", "undated", "none", "null"}:
        return None

    # ISO-ish: 2026-08-09 or 2026-08-09T12:00:00Z
    iso = re.match(r"^(\d{4}-\d{2}-\d{2})(?:[T\s].*)?$", s)
    if iso:
        try:
            return datetime.strptime(iso.group(1), "%Y-%m-%d")
        except ValueError:
            pass

    for fmt in (
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %d %Y",
        "%B %d %Y",
        "%d %b %Y",
        "%d %B %Y",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue

    # Numeric slash/dash dates
    m = re.match(r"^(\d{1,4})[./-](\d{1,2})[./-](\d{1,4})$", s)
    if m:
        a, b, c = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        # Year-first
        if a >= 1900 and a <= 2100 and 1 <= b <= 12 and 1 <= c <= 31:
            try:
                return datetime(a, b, c)
            except ValueError:
                return None
        # Year-last: prefer MDY (US), fall back to DMY when month invalid
        year = c if c >= 100 else (2000 + c if c < 100 else c)
        if year < 1900 or year > 2100:
            return None
        if 1 <= a <= 12 and 1 <= b <= 31:
            try:
                return datetime(year, a, b)  # MDY
            except ValueError:
                pass
        if 1 <= b <= 12 and 1 <= a <= 31:
            try:
                return datetime(year, b, a)  # DMY
            except ValueError:
                pass
    return None


def format_display_date(raw: Any) -> Optional[str]:
    """Normalize a date string to 'Mon D, YYYY' for UI/summary consistency."""
    dt = parse_mention_date(raw)
    if not dt:
        cleaned = _clean_date_text(raw)
        return cleaned or None
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}"


SYSTEM_PROMPT_TEMPLATE = """
You are analyzing public mentions of a missing person named {name}.
Below are raw text snippets from various public sources.

Extract ONLY mentions that clearly refer to this exact person (full name match
or unambiguous reference). Do NOT include unrelated people who only share a
first name or last name.

Prefer mentions that contain at least one of:
- A location (city, neighborhood, street, landmark)
- A time or date reference
- A physical description
- A sighting / "last seen" / "missing" news context

Also include public social/profile pages that clearly belong to this exact name
(Facebook, Instagram, LinkedIn, etc.) even if they lack a location.
Mark those confidence as "low" and put location as "" unless stated.

For each valid mention return JSON:
{{
  "source": "platform name",
  "date": "date if mentioned",
  "location": "location if mentioned",
  "quote": "exact relevant quote under 100 words (or page title if that is all you have)",
  "confidence": "high/medium/low",
  "url": "source url",
  "kind": "sighting|news|profile|other"
}}

Ignore spam and people who only share a first name or last name.
Include every distinct public page/post that clearly refers to this person
(news, social, posters, family appeals) — duplicates from reposts are OK.
If the only hits are profile pages for this exact name, still return them as low-confidence profile mentions.
Return only a JSON array. Nothing else.
""".strip()


def _name_tokens(name: str) -> List[str]:
    return [t for t in re.split(r"\s+", (name or "").strip().lower()) if len(t) > 1]


def _name_match_strength(name: str, blob: str, url: str = "") -> str:
    """
    Return 'full' | 'strong' | 'weak' | 'none'.
    full   = exact full-name phrase
    strong = first + last as whole words
    weak   = first-only / last-in-url (not enough alone)
    """
    name_l = " ".join((name or "").split()).lower()
    tokens = _name_tokens(name)
    text = f"{blob or ''} {url or ''}".lower()
    if not name_l or not text.strip():
        return "none"
    if name_l in text:
        return "full"
    if len(tokens) >= 2:
        first_re = re.compile(rf"\b{re.escape(tokens[0])}\b", re.I)
        last_re = re.compile(rf"\b{re.escape(tokens[-1])}\b", re.I)
        if first_re.search(blob or "") and last_re.search(blob or ""):
            return "strong"
        if first_re.search(blob or "") and tokens[-1] in (url or "").lower():
            return "weak"
        if first_re.search(blob or "") or last_re.search(blob or ""):
            return "weak"
    elif tokens and re.search(rf"\b{re.escape(tokens[0])}\b", text, re.I):
        return "strong"
    return "none"


def _mentions_person(name: str, item: Dict[str, Any]) -> bool:
    blob = f"{item.get('title') or ''} {item.get('quote') or item.get('text') or item.get('snippet') or ''}"
    url = item.get("url") or ""
    return _name_match_strength(name, blob, url) in {"full", "strong"}


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
    Strict fallback extractor used when Gemini is unavailable.

    Requires a full/strong name match. Keeps:
    - missing / last-seen / sighting context near the name (not SERP mashups)
    - location + time signals
    - true social profile URLs for this exact name
    Rejects first-name-only / vague web hits (major source of inaccurate finds).
    """
    location_words = re.compile(
        r"\b(in|near|around|at|from)\s+[A-Z][A-Za-z0-9 .'-]{2,40}",
    )
    time_words = re.compile(
        r"\b(yesterday|today|last\s+night|last\s+week|monday|tuesday|wednesday|"
        r"thursday|friday|saturday|sunday|january|february|march|april|may|june|"
        r"july|august|september|october|november|december|\d{1,2}/\d{1,2}/\d{2,4}|"
        r"20\d{2}|missing|last\s+seen|sighting)\b",
        re.I,
    )
    signal_words = re.compile(
        r"\b(missing|last\s+seen|sighting|abducted|disappeared|have\s+you\s+seen|"
        r"looking\s+for|please\s+help|amber\s+alert)\b",
        re.I,
    )
    social_hosts = ("facebook.com", "instagram.com", "tiktok.com", "x.com", "twitter.com", "linkedin.com")
    social_sources = {"instagram", "facebook", "tiktok", "x", "twitter", "linkedin"}

    name_l = " ".join(name.split()).lower()
    tokens = _name_tokens(name)

    def _signal_near_name(blob: str) -> bool:
        """Require missing/sighting language near the person's name (filters SERP mashups)."""
        low = blob.lower()
        anchors = [name_l] if name_l in low else []
        if tokens:
            # last name is a stronger anchor than first
            anchors.append(tokens[-1])
            anchors.append(tokens[0])
        for a in anchors:
            start = 0
            while True:
                idx = low.find(a, start)
                if idx < 0:
                    break
                window = blob[max(0, idx - 100) : idx + len(a) + 140]
                if signal_words.search(window):
                    return True
                start = idx + len(a)
        return bool(signal_words.search(blob)) and name_l in low

    out: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()
    for item in raw_mentions:
        title = item.get("title") or ""
        text = item.get("text") or item.get("snippet") or ""
        blob = f"{title} {text}"
        url = (item.get("url") or "").lower()
        source = (item.get("source") or "web").lower()

        strength = _name_match_strength(name, blob, url)
        if strength not in {"full", "strong"}:
            continue

        has_loc = bool(location_words.search(blob))
        has_time = bool(time_words.search(blob)) or bool(item.get("date"))
        has_signal = _signal_near_name(blob)
        is_social_url = any(h in url for h in social_hosts)
        is_social_src = source in social_sources
        is_profile = (is_social_url or is_social_src) and strength in {"full", "strong"}
        title_has_name = _name_match_strength(name, title, "") in {"full", "strong"}

        # Web/news: keep if signal near name, OR title is clearly this person,
        # OR full-name phrase appears (restores Gemini-like coverage without weak first-name hits)
        if source in {"google", "web", "news", "youtube"} and not is_profile:
            if not (
                has_signal
                or title_has_name
                or (strength == "full" and (has_loc or has_time or has_signal))
                or strength == "full"
            ):
                continue
        elif not (
            has_signal
            or (has_loc and has_time)
            or is_profile
            or (strength == "full")
        ):
            continue

        # Drop obvious SERP mashups: title is unrelated AND name only appears late in blob
        if source in {"google", "web", "news"} and not title_has_name and strength == "full":
            low = blob.lower()
            idx = low.find(name_l) if name_l else -1
            if idx > 160 and not has_signal:
                continue

        loc_match = location_words.search(blob)
        if has_signal and (has_loc or has_time or title_has_name):
            confidence = "medium"
            kind = "sighting" if re.search(r"sight|last\s+seen", blob, re.I) else "news"
        elif is_profile and not (has_loc or has_signal):
            confidence = "low"
            kind = "profile"
        elif title_has_name or strength == "full":
            confidence = "low"
            kind = "news" if has_signal else "other"
        else:
            confidence = "low"
            kind = "news" if has_signal else "other"

        location = ""
        if loc_match:
            location = re.sub(
                r"^(in|near|around|at|from)\s+", "", loc_match.group(0), flags=re.I
            ).strip()

        url_key = url.split("?")[0] if url else f"{source}:{title[:60]}"
        if url_key in seen_urls:
            continue
        seen_urls.add(url_key)

        out.append(
            {
                "source": item.get("source") or "web",
                "date": format_display_date(item.get("date")) or "",
                "location": location,
                "quote": (text or title or "Public page mentioning this name")[:400],
                "confidence": confidence,
                "url": item.get("url") or "",
                "kind": kind,
            }
        )
        if len(out) >= 60:
            break
    return out


def _parse_retry_seconds(exc: BaseException) -> float:
    msg = str(exc)
    m = re.search(r"retry(?:_delay)?[^\d]*(\d+(?:\.\d+)?)\s*s", msg, re.I)
    if m:
        return min(60.0, max(5.0, float(m.group(1))))
    m = re.search(r"Please retry in\s+(\d+(?:\.\d+)?)", msg, re.I)
    if m:
        return min(60.0, max(5.0, float(m.group(1))))
    return 8.0


def _normalize_mention(m: Dict[str, Any]) -> Dict[str, Any]:
    conf = str(m.get("confidence") or "low").lower()
    if conf not in {"high", "medium", "low"}:
        conf = "low"
    return {
        "source": str(m.get("source") or "web")[:60],
        "date": format_display_date(m.get("date")) or "",
        "location": str(m.get("location") or "")[:120],
        "quote": str(m.get("quote") or "")[:500],
        "confidence": conf,
        "url": str(m.get("url") or "")[:500],
        "kind": str(m.get("kind") or "other")[:40],
    }


def extract_sightings_with_gemini(
    name: str,
    raw_mentions: List[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], str]:
    """
    Send raw mentions to Gemini and return (sightings, engine).
    engine is 'gemini' | 'heuristic' | 'heuristic_fallback'.
    Retries / rotates models on 429; falls back to a strict heuristic.
    """
    from services.gemini_client import (
        get_generative_model,
        iter_model_fallbacks,
        mark_model_rate_limited,
    )

    if not raw_mentions:
        return [], "empty"

    # Cap payload size for the model (prefer higher-signal first)
    ranked = sorted(
        raw_mentions,
        key=lambda it: (
            0 if _name_match_strength(
                name,
                f"{it.get('title') or ''} {it.get('text') or it.get('snippet') or ''}",
                it.get("url") or "",
            ) == "full"
            else 1 if _name_match_strength(
                name,
                f"{it.get('title') or ''} {it.get('text') or it.get('snippet') or ''}",
                it.get("url") or "",
            ) == "strong"
            else 2
        ),
    )
    payload = []
    for item in ranked[:80]:
        payload.append(
            {
                "source": item.get("source"),
                "date": item.get("date"),
                "url": item.get("url"),
                "text": (item.get("text") or item.get("snippet") or item.get("title") or "")[:600],
            }
        )

    if not gemini_configured():
        logger.info("Gemini not configured — using heuristic extractor")
        return _heuristic_extract(name, raw_mentions), "heuristic"

    prompt = (
        f"Person name: {name}\n\n"
        f"Raw mentions JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    system = SYSTEM_PROMPT_TEMPLATE.format(name=name)
    last_exc: Optional[BaseException] = None
    models = iter_model_fallbacks()
    primary = models[0] if models else None

    for model_name in models:
        # Skip models already cooling from earlier 429s this process
        try:
            model = get_generative_model(
                system_instruction=system,
                model_name=model_name,
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
            cleaned = [_normalize_mention(m) for m in mentions]
            cleaned = [m for m in cleaned if _mentions_person(name, m)]
            if cleaned:
                # Supplement with strict full-name heuristic hits Gemini omitted
                # (restores coverage toward the larger accurate set users saw before).
                seen = {(c.get("url") or "").split("?")[0] for c in cleaned}
                for h in _heuristic_extract(name, raw_mentions):
                    key = (h.get("url") or "").split("?")[0]
                    if key and key in seen:
                        continue
                    if not key and (h.get("quote") or "")[:80] in {
                        (c.get("quote") or "")[:80] for c in cleaned
                    }:
                        continue
                    cleaned.append(h)
                    if key:
                        seen.add(key)
                logger.info(
                    "Gemini extract OK via %s — %d mentions (from %d raw)",
                    model_name,
                    len(cleaned),
                    len(raw_mentions),
                )
                return cleaned, "gemini"
            logger.info("Gemini %s returned 0 usable mentions — trying next", model_name)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            msg = str(exc).lower()
            is_429 = "429" in msg or "quota" in msg or "rate" in msg
            is_404 = "404" in msg or "not found" in msg or "no longer available" in msg
            if is_404:
                from services.gemini_client import mark_model_unavailable

                mark_model_unavailable(model_name)
                logger.warning("Gemini %s unavailable — rotating", model_name)
                continue
            if is_429:
                wait = _parse_retry_seconds(exc)
                mark_model_rate_limited(model_name, min(wait, 60.0))
                # One short retry only for the primary model; otherwise rotate immediately
                if model_name == primary and wait <= 12:
                    logger.warning(
                        "Gemini %s 429 — brief retry in %.0fs",
                        model_name,
                        wait,
                    )
                    time.sleep(wait)
                    try:
                        model = get_generative_model(
                            system_instruction=system,
                            model_name=model_name,
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
                        cleaned = [_normalize_mention(m) for m in mentions]
                        cleaned = [m for m in cleaned if _mentions_person(name, m)]
                        if cleaned:
                            return cleaned, "gemini"
                    except Exception as exc2:  # noqa: BLE001
                        last_exc = exc2
                        mark_model_rate_limited(model_name, _parse_retry_seconds(exc2))
                logger.warning("Gemini %s rate-limited — rotating", model_name)
                continue
            logger.warning("Gemini %s failed (%s)", model_name, exc)
            continue

    logger.warning(
        "Gemini extraction exhausted (%s) — strict heuristic fallback",
        last_exc or "empty",
    )
    return _heuristic_extract(name, raw_mentions), "heuristic_fallback"


async def geocode_location(client: httpx.AsyncClient, location: str) -> Optional[Dict[str, float]]:
    """Geocode a free-text location (uses shared robust Nominatim helper)."""
    _ = client
    hit = await asyncio.to_thread(geocode_query, location)
    if not hit:
        return None
    return {
        "lat": float(hit["lat"]),
        "lng": float(hit["lng"]),
        "label": location,
    }


def _drop_geo_outliers(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop points far from the densest cluster (bad geocodes → world-zoom maps)."""
    if len(points) < 2:
        return points
    coords = []
    for p in points:
        try:
            coords.append((float(p["lat"]), float(p["lng"]), p))
        except (TypeError, ValueError, KeyError):
            continue
    if len(coords) < 2:
        return points

    def dist_km(a, b) -> float:
        # Equirectangular approx — fine for outlier screening
        import math

        lat1, lng1 = math.radians(a[0]), math.radians(a[1])
        lat2, lng2 = math.radians(b[0]), math.radians(b[1])
        x = (lng2 - lng1) * math.cos((lat1 + lat2) / 2)
        y = lat2 - lat1
        return 6371.0 * math.sqrt(x * x + y * y)

    # Score each point by how many neighbors are within 250km
    best_i = 0
    best_n = -1
    for i, c in enumerate(coords):
        n = sum(1 for o in coords if dist_km(c, o) <= 250)
        if n > best_n:
            best_n = n
            best_i = i
    anchor = coords[best_i]
    kept = [c[2] for c in coords if dist_km(anchor, c) <= 250]
    return kept or points


async def geocode_mentions(
    sightings: List[Dict[str, Any]],
    raw_mentions: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Geocode unique location strings from sightings (and raw mention text as fallback).
    Returns list of {lat, lng, label, count} for the heatmap.
    """
    counts: Counter = Counter()
    for s in sightings:
        loc = (s.get("location") or "").strip()
        loc = re.sub(r"^(in|near|around|at|from)\s+", "", loc, flags=re.I).strip()
        if loc and loc.lower() not in {"unknown", "n/a", "none", "null"}:
            counts[loc] += 1

    if not counts and raw_mentions:
        phrase = re.compile(
            r"\b(?:in|near|around|at)\s+([A-Z][A-Za-z0-9 .'-]{2,48})",
        )
        for m in raw_mentions:
            blob = f"{m.get('title') or ''} {m.get('text') or m.get('snippet') or ''}"
            for match in phrase.finditer(blob):
                label = match.group(1).strip(" .,")
                if len(label) >= 2:
                    counts[label] += 1

    if not counts:
        return []

    def _ok_label(label: str) -> bool:
        t = (label or "").strip()
        if len(t) < 3:
            return False
        if re.match(r"^[a-z]\s", t):  # e.g. "m Lily" from truncated text
            return False
        if t.lower() in {"unknown", "n/a", "none", "null", "the", "a", "an"}:
            return False
        # Need a letter run of length >= 3
        return bool(re.search(r"[A-Za-z]{3,}", t))

    locations: List[Dict[str, Any]] = []
    for label in list(counts.keys())[:25]:
        if not _ok_label(label):
            continue
        hit = await asyncio.to_thread(geocode_query, label)
        if not hit:
            continue
        locations.append(
            {
                "lat": float(hit["lat"]),
                "lng": float(hit["lng"]),
                "label": label,
                "count": counts[label],
            }
        )
        await asyncio.sleep(0.15)

    return _drop_geo_outliers(locations)


def build_summary(
    name: str,
    photo_data_url: Optional[str],
    sightings: List[Dict[str, Any]],
    locations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Assemble the SUMMARY block for the report."""
    parsed = []
    for s in sightings:
        dt = parse_mention_date(s.get("date"))
        if dt:
            parsed.append(dt)
    parsed.sort()
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
            "start": format_display_date(parsed[0]) if parsed else None,
            "end": format_display_date(parsed[-1]) if parsed else None,
        },
        "most_frequent_location": top_location or None,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def sort_sightings_chronologically(sightings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort by parsed date when possible; undated items go last. Normalize date display."""

    decorated = []
    for item in sightings:
        dt = parse_mention_date(item.get("date"))
        normalized = dict(item)
        if dt:
            normalized["date"] = format_display_date(dt) or ""
        elif item.get("date"):
            normalized["date"] = _clean_date_text(item.get("date"))
        decorated.append((0 if dt else 1, dt or datetime.max, normalized))

    decorated.sort(key=lambda x: (x[0], x[1]))
    return [x[2] for x in decorated]
