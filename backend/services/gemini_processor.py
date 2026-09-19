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
from urllib.parse import urlparse

from services.gemini_client import gemini_configured
from services.geocode import geocode_query

logger = logging.getLogger(__name__)

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

    # Normalize common abbreviations (Sept. → Sep)
    s = re.sub(r"\bSept\.?\b", "Sep", s, flags=re.I)
    s = re.sub(r"\b([A-Za-z]{3,9})\.", r"\1", s)  # Oct. → Oct

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
Below are raw text snippets from public web and social sources (including
individual social-media comments with usernames when available).

Extract ONLY items that clearly refer to this exact person.
Do NOT include unrelated people who only share a first or last name.
Do NOT include pure "prayers / sharing / tagging / awareness" posts with no new facts.
Do NOT treat Google SERP mashups (unrelated headline + "..." + missing-person blurb) as sightings.

Kinds:
- sighting = a WITNESS claim (someone says they personally saw/spotted the person).
  Examples: "I saw her near Crystal City last night", "think I spotted him at the metro".
  NOT sighting: news saying "was last seen on Sept 15", family pleas, TikTok awareness videos.
- news = media / official missing-person reporting (last-seen facts, searches underway).
- profile = social profile pages for this exact name.
- other = everything else that still clearly refers to this person.

For each valid item return JSON:
{{
  "source": "platform name (reddit/instagram/facebook/google/news/...)",
  "username": "commenter or poster handle if known, else empty string",
  "date": "sighting date if known for kind=sighting; else article/post date",
  "time": "time of day if known (e.g. evening, 7pm), else empty string",
  "location": "place / vicinity if known, else empty string",
  "quote": "short exact quote under 80 words — ONLY the part about {name}, never unrelated headlines",
  "claim_summary": "For kind=sighting only: [username] on [platform] claims to have seen the person on [date] at around [time] near [place]. For news: [Outlet] reports that {name} was last seen on [date] near [place]. Omit unknown parts.",
  "confidence": "high/medium/low",
  "url": "source url",
  "kind": "sighting|news|profile|other"
}}

Use kind=sighting ONLY for first-person / witness language. Prefer claim dates near the case's reported disappearance window when that is clear from the snippets.
Return only a JSON array. Nothing else.
""".strip()


_WITNESS_RE = re.compile(
    r"\b("
    r"i\s+(just\s+)?(saw|spotted|noticed|witnessed)|"
    r"we\s+(saw|spotted|noticed)|"
    r"think\s+i\s+saw|might\s+have\s+seen|believe\s+i\s+saw|"
    r"claimed\s+to\s+(have\s+)?seen|"
    r"saw\s+(him|her|them|someone|a\s+(girl|woman|guy|man|person))|"
    r"spotted\s+(him|her|them|someone)|"
    r"witness(ed)?\b"
    r")",
    re.I,
)
_OFFICIAL_LAST_SEEN_RE = re.compile(
    r"\b("
    r"was\s+last\s+seen|last\s+seen(?:\s+on|\s+leaving|\s+near|\s+at)?|"
    r"reported\s+missing|search\s+(is\s+)?underway|"
    r"pleads?\s+for|family\s+(of|pleads)|raising\s+awareness|missing\s+person|"
    r"have\s+you\s+seen|please\s+share|amber\s+alert"
    r")\b",
    re.I,
)
_MASHUP_NOISE_RE = re.compile(
    r"\b("
    r"senator|lindsey\s+graham|traitor|arrested|grand\s+prix|junk\s+food|"
    r"coach,\s*5\s+teens|track\s+conditions|verbal\s+attacks|53-year-old"
    r")\b",
    re.I,
)

# People-finder / phonebook pages — not sighting intelligence
_DIRECTORY_HOSTS = (
    "whitepages.com",
    "usphonebook.com",
    "radaris.com",
    "fastbackgroundcheck.com",
    "spokeo.com",
    "beenverified.com",
    "intelius.com",
    "peoplefinders.com",
    "truepeoplesearch.com",
    "thatsthem.com",
    "anywho.com",
    "addresses.com",
    "familytreenow.com",
    "checkpeople.com",
    "instantcheckmate.com",
)

_OTHER_CASE_BEFORE_RE = re.compile(
    r"\b("
    r"last\s+seen|missing\s+person|missing\s+adult|please\s+help|"
    r"have\s+you\s+seen|amber\s+alert|search\s+underway|"
    r"if\s+you\s+have\s+seen|spread\s+the\s+word|looking\s+for\s+this\s+missing"
    r")\b",
    re.I,
)


def _person_span(name: str, text: str) -> tuple[int, int]:
    """
    Start/end index of the best person-name hit in text.
    Prefers full name, then last-name + compatible first nearby (Abra≈Albra).
    Never treats a lone surname in a phonebook list as the hit.
    """
    low = (text or "").lower()
    name_l = " ".join((name or "").split()).lower()
    tokens = _name_tokens(name)
    if not low.strip() or not name_l:
        return -1, -1
    idx = low.find(name_l)
    if idx >= 0:
        return idx, idx + len(name_l)
    if len(tokens) < 2:
        m = re.search(rf"\b{re.escape(tokens[0])}\b", low) if tokens else None
        return (m.start(), m.end()) if m else (-1, -1)
    first, last = tokens[0], tokens[-1]
    for m in re.finditer(rf"\b{re.escape(last)}\b", low):
        window = low[max(0, m.start() - 48) : m.end() + 24]
        for w in re.findall(r"[a-z]{2,}", window):
            if w == last:
                continue
            if w == first or _first_names_compatible(first, w):
                # Prefer start of the first-name token in the window
                w_idx = window.find(w)
                start = max(0, m.start() - 48) + w_idx if w_idx >= 0 else m.start()
                return start, m.end()
    return -1, -1


def _title_about_person(name: str, title: str) -> bool:
    return _name_match_strength(name, title or "", "") in {"full", "strong"}


def _is_directory_url(url: str) -> bool:
    host = (urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return any(host == h or host.endswith("." + h) for h in _DIRECTORY_HOSTS)


def _quote_about_person(name: str, quote: str) -> str:
    """Keep only the clause that mentions the person (drop SERP mashup head)."""
    q = (quote or "").strip()
    if not q:
        return ""
    start, end = _person_span(name, q)
    if start > 40:
        return q[start:][:400].strip(" .…")
    if start >= 0 and end - start < 8:
        # Expand a tiny name-only slice
        return q[start : min(len(q), start + 280)].strip(" .…")
    if "..." in q or "…" in q:
        parts = re.split(r"\.\.\.|…", q)
        for part in reversed(parts):
            if _person_span(name, part)[0] >= 0:
                return part.strip(" .…")[:400]
    return q[:400]


def _is_serp_mashup(item: Dict[str, Any], name: str = "") -> bool:
    """
    True when SERP/Facebook concatenated an unrelated missing-person post
    with a blurb that merely mentions our person.
    """
    quote = item.get("quote") or item.get("snippet") or item.get("text") or ""
    title = item.get("title") or ""
    url = item.get("url") or ""
    blob = f"{title} {quote}"
    low = blob.lower()
    start, _ = _person_span(name, blob)
    title_has = _title_about_person(name, title)

    if _is_directory_url(url):
        return True

    noise = _MASHUP_NOISE_RE.search(low)
    if noise and start > noise.start():
        return True

    # Unrelated missing-person / last-seen story appears BEFORE our person
    if start > 50:
        before = low[:start]
        if _OTHER_CASE_BEFORE_RE.search(before) and not title_has:
            return True
        # Ellipsis-joined SERP mashups
        if ("..." in blob or "…" in blob) and not title_has:
            return True

    # Title is clearly about a different missing case
    if title and not title_has:
        if _OTHER_CASE_BEFORE_RE.search(title) and start > 30:
            return True

    return False


def _story_fingerprint(name: str, item: Dict[str, Any]) -> str:
    """Collapse near-duplicate shares of the same Abra/Albra update text."""
    blob = f"{item.get('title') or ''} {item.get('text') or item.get('snippet') or ''}"
    start, end = _person_span(name, blob)
    if start < 0:
        core = re.sub(r"\s+", " ", blob.lower())[:120]
    else:
        core = re.sub(r"\s+", " ", blob[max(0, start - 20) : start + 160].lower())
    core = re.sub(r"[^a-z0-9 ]+", "", core)
    return core[:100]


def format_claim_line(item: Dict[str, Any]) -> str:
    """Witness phrasing only for true sightings; never for news mashups."""
    kind = (item.get("kind") or "").lower()
    quote = item.get("quote") or ""
    summary = str(item.get("claim_summary") or "").strip()
    if (
        kind == "sighting"
        and summary
        and _WITNESS_RE.search(f"{quote} {summary}")
        and "claims to have seen" in summary.lower()
    ):
        return summary

    source = (item.get("source") or "web").strip()
    user = (item.get("username") or "").strip().lstrip("@")
    if user:
        handle = (
            f"@{user}"
            if source.lower()
            in {"instagram", "twitter", "x", "tiktok", "reddit", "facebook"}
            else user
        )
    else:
        handle = "Someone"

    date = (item.get("date") or "").strip()
    time_s = (item.get("time") or "").strip()
    place = (item.get("location") or item.get("place") or "").strip()

    if kind != "sighting":
        parts = [f"{handle} on {source} reports about the person"]
        if date:
            parts.append(f"(dated {date})")
        if place:
            parts.append(f"near {place}")
        return " ".join(parts)

    parts = [f"{handle} on {source} claims to have seen the person"]
    if date:
        parts.append(f"on {date}")
    if time_s:
        parts.append(f"at around {time_s}")
    if place:
        parts.append(f"near {place}")
    return " ".join(parts)


def _name_tokens(name: str) -> List[str]:
    return [t for t in re.split(r"\s+", (name or "").strip().lower()) if len(t) > 1]


def _levenshtein(a: str, b: str) -> int:
    """Small edit distance for first-name typo tolerance (Abra ≈ Albra)."""
    a, b = (a or "").lower(), (b or "").lower()
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if abs(len(a) - len(b)) > 2:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (0 if ca == cb else 1)))
        prev = cur
    return prev[-1]


def _first_names_compatible(query_first: str, candidate: str) -> bool:
    q, c = (query_first or "").lower(), (candidate or "").lower()
    if not q or not c or len(c) < 2:
        return False
    if q == c:
        return True
    # Allow one-character typos / missing letter (Albra ↔ Abra)
    return _levenshtein(q, c) <= 1


def _name_match_strength(name: str, blob: str, url: str = "") -> str:
    """
    Return 'full' | 'strong' | 'weak' | 'none'.
    full   = exact full-name phrase
    strong = first+last as whole words, OR last name + first within edit-distance 1
             (handles Abra/Albra). Never last-name-only (rejects Ajet Lleshi for Albra).
    weak   = last-only / first-only / last-in-url
    """
    name_l = " ".join((name or "").split()).lower()
    tokens = _name_tokens(name)
    text = f"{blob or ''} {url or ''}".lower()
    blob_l = (blob or "").lower()
    if not name_l or not text.strip():
        return "none"
    if name_l in text:
        return "full"
    if len(tokens) < 2:
        if tokens and re.search(rf"\b{re.escape(tokens[0])}\b", text, re.I):
            return "strong"
        return "none"

    first, last = tokens[0], tokens[-1]
    last_re = re.compile(rf"\b{re.escape(last)}\b", re.I)
    first_re = re.compile(rf"\b{re.escape(first)}\b", re.I)

    # Exact first + last as separate whole words in the text body
    if first_re.search(blob_l) and last_re.search(blob_l):
        return "strong"

    # Last name present + nearby first-name token within edit distance 1
    if last_re.search(blob_l):
        for m in last_re.finditer(blob_l):
            window = blob_l[max(0, m.start() - 48) : m.end() + 24]
            for word in re.findall(r"[a-z]{2,}", window):
                if word == last:
                    continue
                if _first_names_compatible(first, word):
                    return "strong"
        # last name only (different person sharing surname) → weak
        if first_re.search(blob_l) or first_re.search(text):
            return "strong"
        if last in (url or "").lower() and first_re.search(blob_l):
            return "strong"
        return "weak"

    if first_re.search(blob_l) and last in (url or "").lower():
        return "weak"
    if first_re.search(blob_l) or last_re.search(blob_l):
        return "weak"
    return "none"


def mention_matches_person(name: str, item: Dict[str, Any]) -> bool:
    """True when a raw or extracted mention is about this specific person."""
    blob = (
        f"{item.get('title') or ''} {item.get('quote') or item.get('text') or item.get('snippet') or ''} "
        f"{item.get('claim_summary') or ''} {item.get('username') or ''}"
    )
    url = item.get("url") or ""
    if _name_match_strength(name, blob, url) in {"full", "strong"}:
        return True
    # Username handle like albralleshi / abra.lleshi (not random Lleshi relatives)
    tokens = _name_tokens(name)
    handle = re.sub(r"[^a-z0-9]", "", (item.get("username") or "").lower())
    if len(tokens) >= 2 and len(handle) >= 5:
        first, last = tokens[0], tokens[-1]
        if last in handle:
            remainder = handle.replace(last, "", 1)
            if remainder and (
                _first_names_compatible(first, remainder)
                or remainder == first
            ):
                return True
    return False


def filter_raw_mentions_for_person(
    name: str, raw_mentions: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Drop scrapes about other people / keyword noise / SERP mashups / directories
    before extraction or UI. Dedupes near-identical shared updates.
    """
    kept: List[Dict[str, Any]] = []
    seen_fp: set[str] = set()
    for item in raw_mentions or []:
        url = item.get("url") or ""
        if _is_directory_url(url):
            continue
        if not mention_matches_person(name, item):
            continue
        if _is_serp_mashup(item, name):
            continue
        fp = _story_fingerprint(name, item)
        if fp and fp in seen_fp:
            continue
        if fp:
            seen_fp.add(fp)
        kept.append(item)
    if len(kept) != len(raw_mentions or []):
        logger.info(
            "Name/mashup filter: %d → %d raw mentions for %r",
            len(raw_mentions or []),
            len(kept),
            name,
        )
    return kept


def _mentions_person(name: str, item: Dict[str, Any]) -> bool:
    if mention_matches_person(name, item):
        return True
    # Comments often omit the name when the parent post is about the person
    title = item.get("title") or ""
    if "comment on" in title.lower() and _name_match_strength(name, title, "") in {"full", "strong"}:
        return True
    return False


def _enrich_mentions_from_raw(
    cleaned: List[Dict[str, Any]],
    raw_mentions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Backfill username/time from raw Apify rows when the model omits them."""
    by_url: Dict[str, Dict[str, Any]] = {}
    for r in raw_mentions:
        u = (r.get("url") or "").split("?")[0].rstrip("/")
        if u and u not in by_url:
            by_url[u] = r
    for m in cleaned:
        u = (m.get("url") or "").split("?")[0].rstrip("/")
        raw = by_url.get(u) or {}
        if not m.get("username") and raw.get("username"):
            m["username"] = str(raw["username"]).lstrip("@")[:80]
        if not m.get("time") and raw.get("time"):
            m["time"] = str(raw["time"])[:40]
        m["claim_summary"] = format_claim_line(m)
    return cleaned


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
        r"\b(?:in|near|around|at|from)\s+([A-Z][A-Za-z]+(?:[\s,-]+[A-Z][A-Za-z]+){0,3})",
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
        """Require missing/sighting language near the person's name (not surname alone)."""
        low = blob.lower()
        anchors: List[str] = []
        if name_l in low:
            anchors.append(name_l)
        if len(tokens) >= 2:
            # Prefer first+last window; never treat last-name-only as enough
            first, last = tokens[0], tokens[-1]
            for m in re.finditer(rf"\b{re.escape(last)}\b", low):
                window = low[max(0, m.start() - 48) : m.end() + 24]
                words = re.findall(r"[a-z]{2,}", window)
                if any(w == first or _first_names_compatible(first, w) for w in words if w != last):
                    anchors.append(last)
                    break
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

        # Drop obvious SERP mashups: noise headline + person name later
        if _is_serp_mashup({"title": title, "quote": text}, name):
            continue

        # Drop Google mashups where title is unrelated AND name only appears late
        if source in {"google", "web", "news"} and not title_has_name and strength == "full":
            low = blob.lower()
            idx = low.find(name_l) if name_l else -1
            if idx > 160 and not has_signal:
                continue
            if idx > 80 and _MASHUP_NOISE_RE.search(low[:idx]):
                continue

        # Only read places from a window around THIS person's name
        p_start, p_end = _person_span(name, blob)
        near = blob[max(0, p_start - 60) : p_end + 180] if p_start >= 0 else blob[:220]
        loc_match = location_words.search(near)
        of_match = re.search(
            r"\b(?:of|in|near|from)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})",
            near,
        )
        is_witness = bool(_WITNESS_RE.search(near))
        is_official = bool(_OFFICIAL_LAST_SEEN_RE.search(near)) and not is_witness
        if is_witness and (has_loc or has_time or title_has_name):
            confidence = "medium"
            kind = "sighting"
        elif has_signal and (has_loc or has_time or title_has_name):
            confidence = "medium"
            kind = "news" if is_official or has_signal else "other"
        elif re.search(
            r"\b(sister|brother|family|made\s+contact|says?\s+she.?s\s+safe|"
            r"missing\s+adult|concerned\s+about\s+her\s+safety)\b",
            near,
            re.I,
        ):
            confidence = "medium"
            kind = "news"
        elif (item.get("kind") or "").lower() == "comment" and is_witness and (has_loc or has_time):
            confidence = "medium"
            kind = "sighting"
        elif is_profile and not (has_loc or has_signal):
            confidence = "low"
            kind = "profile"
        elif title_has_name or strength == "full":
            confidence = "low"
            kind = "news" if (has_signal or is_official) else "other"
        else:
            confidence = "low"
            kind = "news" if has_signal else "other"

        # Never label official last-seen / mashups as sightings
        if kind == "sighting" and (is_official or _is_serp_mashup({"title": title, "quote": text}, name)):
            kind = "news"

        def _clean_place(raw: str) -> str:
            location = (raw or "").strip(" .,")
            _place_stop = {
                "she", "he", "they", "i", "we", "and", "says", "said", "made",
                "contact", "was", "is", "are", "the", "a", "an", "this", "my",
                "her", "his", "their", "who", "that", "with", "from", "about",
                "under", "influence", "alcohol", "operating", "vehicle",
            }
            parts = []
            for p in re.split(r"[\s,]+", location):
                if not p:
                    continue
                if p.lower() in _place_stop:
                    break
                parts.append(p)
            location = " ".join(parts)
            if (
                not location
                or len(location) > 48
                or len(location.split()) > 4
                or re.search(
                    r"\b(update|safety|reported|missing|found|sister|contact|says|"
                    r"arrested|investigation|driver|operating)\b",
                    location,
                    re.I,
                )
            ):
                return ""
            for tok in tokens:
                if re.search(rf"\b{re.escape(tok)}\b", location, re.I):
                    return ""
            return location

        location = ""
        if loc_match:
            location = _clean_place(loc_match.group(1))
        if not location and of_match:
            location = _clean_place(of_match.group(1))

        quote = _quote_about_person(name, text or title or "")
        # Reject name-only / tiny quotes
        q_compact = re.sub(r"[^a-z0-9 ]", "", quote.lower()).strip()
        name_compact = re.sub(r"[^a-z0-9 ]", "", name_l).strip()
        if not quote or q_compact == name_compact or len(quote) < max(12, len(name) + 3):
            # Prefer longer nearby context
            if p_start >= 0:
                quote = blob[p_start : min(len(blob), p_start + 280)].strip(" .…")
            else:
                quote = (text or title or "")[:280]
            quote = _quote_about_person(name, quote)
        if not quote or len(quote) < 8:
            continue

        url_key = url.split("?")[0] if url else f"{source}:{title[:60]}"
        if url_key in seen_urls:
            continue
        seen_urls.add(url_key)

        out.append(
            {
                "source": item.get("source") or "web",
                "username": (item.get("username") or "").lstrip("@")[:80],
                "date": format_display_date(item.get("date")) or "",
                "time": (item.get("time") or "")[:40],
                "location": location,
                "quote": quote[:400],
                "confidence": confidence,
                "url": item.get("url") or "",
                "kind": kind,
            }
        )
        out[-1]["claim_summary"] = format_claim_line(out[-1])
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


def _normalize_mention(m: Dict[str, Any], name: str = "") -> Dict[str, Any]:
    conf = str(m.get("confidence") or "low").lower()
    if conf not in {"high", "medium", "low"}:
        conf = "low"
    kind = str(m.get("kind") or "other")[:40]
    quote = str(m.get("quote") or "")[:500]
    if name:
        quote = _quote_about_person(name, quote)
    out = {
        "source": str(m.get("source") or "web")[:60],
        "username": str(m.get("username") or "").lstrip("@")[:80],
        "date": format_display_date(m.get("date")) or str(m.get("date") or "")[:40],
        "time": str(m.get("time") or "")[:40],
        "location": str(m.get("location") or m.get("place") or "")[:120],
        "quote": quote,
        "confidence": conf,
        "url": str(m.get("url") or "")[:500],
        "kind": kind,
        "claim_summary": str(m.get("claim_summary") or "")[:400],
    }
    # Demote news / mashups wrongly labeled as sightings
    blob = f"{out['quote']} {out['claim_summary']} {out.get('title') or ''}"
    if out["kind"] == "sighting":
        if _is_serp_mashup(out, name) or (
            _OFFICIAL_LAST_SEEN_RE.search(blob) and not _WITNESS_RE.search(blob)
        ):
            out["kind"] = "news"
    out["claim_summary"] = format_claim_line(out)
    return out


def is_sighting_claim(item: Dict[str, Any], name: str = "") -> bool:
    """
    True only for witness-style sighting claims.
    Excludes news 'was last seen', awareness posts, and SERP mashups.
    """
    if _is_serp_mashup(item, name):
        return False

    kind = (item.get("kind") or "").lower()
    source = (item.get("source") or "").lower()
    quote = item.get("quote") or ""
    summary = item.get("claim_summary") or ""
    blob = f"{quote} {summary} {item.get('title') or ''}"

    # News / official last-seen language is NOT a witness claim
    if _OFFICIAL_LAST_SEEN_RE.search(blob) and not _WITNESS_RE.search(blob):
        return False

    # Google/news rows need explicit first-person witness language
    if source in {"google", "news", "web", "youtube"} and not _WITNESS_RE.search(blob):
        return False

    # Awareness / share posts without witness language
    if re.search(r"\b(raising\s+awareness|please\s+share|have\s+you\s+seen)\b", blob, re.I):
        if not _WITNESS_RE.search(blob):
            return False

    if kind == "sighting" and _WITNESS_RE.search(blob):
        return True
    if kind == "sighting" and item.get("username") and (item.get("location") or item.get("time")):
        # Social commenter with place/time, even if phrasing is terse
        if source in {"reddit", "instagram", "facebook", "tiktok", "x", "twitter"}:
            return True

    if item.get("username") and _WITNESS_RE.search(blob) and (item.get("location") or item.get("time")):
        return True

    return bool(_WITNESS_RE.search(blob) and (item.get("location") or item.get("time")))


def _infer_disappearance_anchor(sightings: List[Dict[str, Any]]) -> Optional[datetime]:
    """Infer likely disappearance / last-seen date from extracted text."""
    candidates: List[datetime] = []
    pat = re.compile(
        r"last\s+seen(?:\s+on|\s+leaving)?\s*"
        r"([A-Za-z]+\.?\s+\d{1,2},?\s+20\d{2}|\d{1,2}/\d{1,2}/20\d{2}|20\d{2}-\d{2}-\d{2})",
        re.I,
    )
    for s in sightings:
        blob = f"{s.get('quote') or ''} {s.get('claim_summary') or ''} {s.get('date') or ''}"
        for m in pat.finditer(blob):
            dt = parse_mention_date(m.group(1))
            if dt:
                candidates.append(dt)
    if not candidates:
        return None
    # Prefer the most common calendar day
    counts = Counter(d.date() for d in candidates)
    best_day = counts.most_common(1)[0][0]
    return datetime(best_day.year, best_day.month, best_day.day)


def _date_near_anchor(item: Dict[str, Any], anchor: datetime, *, before_days: int = 3, after_days: int = 60) -> bool:
    """Keep claim dates near the disappearance window; undated claims are kept."""
    dt = parse_mention_date(item.get("date"))
    if not dt:
        return True
    delta = (dt.date() - anchor.date()).days
    return -before_days <= delta <= after_days


def extract_sighting_claims(
    sightings: List[Dict[str, Any]],
    name: str = "",
) -> List[Dict[str, Any]]:
    """Chronological witness claims only (not news mashups). Mutates sightings in place to demote fakes."""
    for s in sightings:
        if name:
            s["quote"] = _quote_about_person(name, s.get("quote") or "")
        blob = f"{s.get('quote') or ''} {s.get('claim_summary') or ''}"
        if (s.get("kind") or "").lower() == "sighting":
            if _is_serp_mashup(s, name) or (
                _OFFICIAL_LAST_SEEN_RE.search(blob) and not _WITNESS_RE.search(blob)
            ):
                s["kind"] = "news"
        s["claim_summary"] = format_claim_line(s)

    claims = [s for s in sightings if is_sighting_claim(s, name)]
    anchor = _infer_disappearance_anchor(sightings)
    if anchor:
        claims = [c for c in claims if _date_near_anchor(c, anchor)]
    return sort_sightings_chronologically(claims)


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
                "username": item.get("username") or "",
                "kind": item.get("kind") or "post",
                "date": item.get("date"),
                "time": item.get("time") or "",
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
    models = iter_model_fallbacks()[:2]
    if not models:
        logger.warning("Gemini models on cooldown — heuristic extractor")
        return _heuristic_extract(name, raw_mentions), "heuristic_fallback"

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
            cleaned = [_normalize_mention(m, name) for m in mentions]
            cleaned = [m for m in cleaned if _mentions_person(name, m)]
            cleaned = _enrich_mentions_from_raw(cleaned, raw_mentions)
            if cleaned:
                # Supplement with strict full-name heuristic hits Gemini omitted
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
                logger.warning("Gemini %s rate-limited — rotating (no wait)", model_name)
                continue
            logger.warning("Gemini %s failed (%s)", model_name, exc)
            continue

    logger.warning(
        "Gemini extraction exhausted (%s) — strict heuristic fallback",
        last_exc or "empty",
    )
    return _heuristic_extract(name, raw_mentions), "heuristic_fallback"


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
    person_name: str = "",
) -> List[Dict[str, Any]]:
    """
    Geocode unique location strings from sightings (and name-matched raw text as fallback).
    Returns list of {lat, lng, label, count} for the heatmap.
    """
    counts: Counter = Counter()
    for s in sightings:
        loc = (s.get("location") or "").strip()
        loc = re.sub(r"^(in|near|around|at|from)\s+", "", loc, flags=re.I).strip()
        if loc and loc.lower() not in {"unknown", "n/a", "none", "null"}:
            counts[loc] += 1

    if not counts and raw_mentions:
        # Only scan mentions that are about THIS person — never unrelated scrapes
        phrase = re.compile(
            r"\b(?:in|near|around|at)\s+([A-Z][A-Za-z]+(?:[\s,-]+[A-Z][A-Za-z]+){0,3})",
        )
        for m in raw_mentions:
            if person_name and not mention_matches_person(person_name, m):
                continue
            blob = f"{m.get('title') or ''} {m.get('text') or m.get('snippet') or ''}"
            for match in phrase.finditer(blob):
                label = match.group(1).strip(" .,")
                # Cut off at sentence junk
                label = re.split(r"[.!?|/]", label)[0].strip()
                if len(label) >= 2:
                    counts[label] += 1

    if not counts:
        return []

    def _ok_label(label: str) -> bool:
        t = (label or "").strip()
        if len(t) < 3 or len(t) > 48:
            return False
        words = t.split()
        if len(words) > 4:
            return False
        if any(
            w.lower()
            in {
                "she", "he", "they", "says", "said", "made", "contact", "update",
                "safety", "missing", "found",
            }
            for w in words
        ):
            return False
        low = t.lower()
        if low in {"unknown", "n/a", "none", "null", "the", "a", "an"}:
            return False
        # Headlines / non-places that used to become "top location"
        if re.search(
            r"\b(update|safety|reported|missing|found|sister|brother|contact|says)\b",
            low,
        ):
            return False
        if person_name:
            for tok in _name_tokens(person_name):
                if re.search(rf"\b{re.escape(tok)}\b", low):
                    return False
        # Truncated fragments like "Ancho"
        if len(words) == 1 and len(t) < 5:
            return False
        return bool(re.search(r"[A-Za-z]{3,}", t))

    locations: List[Dict[str, Any]] = []
    for label in list(counts.keys())[:8]:
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
        "total_claims": sum(1 for s in sightings if is_sighting_claim(s, name)),
        "date_range": {
            "start": format_display_date(parsed[0]) if parsed else None,
            "end": format_display_date(parsed[-1]) if parsed else None,
        },
        "most_frequent_location": top_location or None,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def sort_sightings_chronologically(sightings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort by parsed date when possible; undated items go last. Normalize date display."""

    def _time_key(raw: str) -> tuple:
        s = (raw or "").strip().lower()
        if not s:
            return (1, 0)
        # crude hour hints for ordering within a day
        m = re.search(r"\b(\d{1,2})\s*(:(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b", s)
        if m:
            hour = int(m.group(1))
            mins = int(m.group(3) or 0)
            ap = m.group(4)[0]
            if ap == "p" and hour < 12:
                hour += 12
            if ap == "a" and hour == 12:
                hour = 0
            return (0, hour * 60 + mins)
        if "morning" in s:
            return (0, 9 * 60)
        if "noon" in s or "afternoon" in s:
            return (0, 14 * 60)
        if "evening" in s:
            return (0, 18 * 60)
        if "night" in s:
            return (0, 21 * 60)
        return (1, 0)

    decorated = []
    for item in sightings:
        dt = parse_mention_date(item.get("date"))
        normalized = dict(item)
        if dt:
            normalized["date"] = format_display_date(dt) or ""
        elif item.get("date"):
            normalized["date"] = _clean_date_text(item.get("date"))
        if not normalized.get("claim_summary"):
            normalized["claim_summary"] = format_claim_line(normalized)
        decorated.append((0 if dt else 1, dt or datetime.max, _time_key(normalized.get("time") or ""), normalized))

    decorated.sort(key=lambda x: (x[0], x[1], x[2]))
    return [x[3] for x in decorated]
