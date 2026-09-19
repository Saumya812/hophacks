"""
Apify-powered social crawlers for Smart Person Search.

Actors (overridable via env):
  - Reddit posts + comments  → scrapeforge/reddit-scraper
  - Instagram posts + comments → apify/instagram-scraper
  - Facebook public posts     → scraper_one/facebook-posts-search

Requires APIFY_TOKEN. When unset, callers should skip these sources.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

# Default public Actor IDs (Apify uses ~ in API paths)
DEFAULT_REDDIT_ACTOR = "scrapeforge~reddit-scraper"
DEFAULT_INSTAGRAM_ACTOR = "apify~instagram-scraper"
DEFAULT_FACEBOOK_ACTOR = "scraper_one~facebook-posts-search"


def _configured(value: Optional[str]) -> bool:
    if not value:
        return False
    upper = value.upper()
    return not upper.startswith("YOUR_") and "PLACEHOLDER" not in upper and len(value) > 8


def apify_enabled() -> bool:
    return _configured(get_settings().apify_token)


def _author_from(item: Dict[str, Any]) -> str:
    """Best-effort username / display name from heterogeneous actor payloads."""
    for key in (
        "username",
        "userName",
        "author",
        "ownerUsername",
        "handle",
        "pageName",
        "user",
    ):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip().lstrip("@")[:80]
        if isinstance(val, dict):
            for nested in ("username", "name", "handle", "id"):
                n = val.get(nested)
                if isinstance(n, str) and n.strip():
                    return n.strip().lstrip("@")[:80]
    owner = item.get("owner")
    if isinstance(owner, dict):
        for nested in ("username", "full_name", "name"):
            n = owner.get(nested)
            if isinstance(n, str) and n.strip():
                return n.strip().lstrip("@")[:80]
    if isinstance(owner, str) and owner.strip():
        return owner.strip().lstrip("@")[:80]
    return ""


def _normalize(
    *,
    source: str,
    title: str = "",
    snippet: str = "",
    url: str = "",
    date: str = "",
    username: str = "",
    kind: str = "post",
    time: str = "",
) -> Dict[str, Any]:
    text = " ".join(part for part in [title, snippet] if part).strip()
    return {
        "source": source,
        "title": (title or "")[:300],
        "snippet": (snippet or text)[:1000],
        "text": text[:2000],
        "url": url or "",
        "date": (date or "")[:40],
        "username": (username or "").lstrip("@")[:80],
        "kind": (kind or "post")[:40],
        "time": (time or "")[:40],
    }


def _date_from(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        try:
            from datetime import datetime, timezone

            return datetime.fromtimestamp(float(value), tz=timezone.utc).strftime("%Y-%m-%d")
        except Exception:  # noqa: BLE001
            return ""
    s = str(value)
    return s[:10] if len(s) >= 10 else s


async def _run_actor(
    client: httpx.AsyncClient,
    actor_id: str,
    run_input: Dict[str, Any],
    *,
    timeout_secs: int = 120,
) -> List[Dict[str, Any]]:
    """
    Run an Actor synchronously and return dataset items.

    POST /v2/acts/{actorId}/run-sync-get-dataset-items
    Waits up to timeout_secs for the run (Apify caps sync waits ~300s).
    """
    settings = get_settings()
    token = settings.apify_token
    if not _configured(token):
        return []

    # Prefer Bearer auth; also pass token query for older Actor routes
    url = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
    try:
        resp = await client.post(
            url,
            params={"token": token, "timeout": timeout_secs},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=run_input,
            timeout=httpx.Timeout(timeout_secs + 15.0, connect=15.0),
        )
        if resp.status_code >= 400:
            logger.warning(
                "Apify actor %s failed (%s): %s",
                actor_id,
                resp.status_code,
                resp.text[:300],
            )
            return []
        data = resp.json()
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        # Some responses wrap items
        items = data.get("items") or data.get("data") or []
        return [x for x in items if isinstance(x, dict)]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Apify actor %s error: %s", actor_id, exc)
        return []


# ---------------------------------------------------------------------------
# Reddit — posts + comments
# ---------------------------------------------------------------------------

async def crawl_reddit(client: httpx.AsyncClient, full_name: str) -> List[Dict[str, Any]]:
    settings = get_settings()
    actor = (settings.apify_reddit_actor or DEFAULT_REDDIT_ACTOR).replace("/", "~")
    name = " ".join(full_name.split())

    items = await _run_actor(
        client,
        actor,
        {
            "searchTerms": [name, f"{name} missing"],
            "maxItems": 15,
            "scrapeComments": True,
            "maxComments": 12,
            "commentDepth": 2,
            "sort": "relevance",
            "timeFilter": "all",
            "maximizeCoverage": False,
            "fetchPostDetails": True,
            "includeNSFW": False,
        },
        timeout_secs=22,
    )

    out: List[Dict[str, Any]] = []
    for item in items:
        item_type = (item.get("itemType") or item.get("type") or "").lower()
        is_comment = item_type == "comment" or bool(item.get("body") and not item.get("title"))

        if is_comment:
            body = item.get("body") or item.get("text") or ""
            post_title = item.get("postTitle") or item.get("title") or "Reddit comment"
            url = (
                item.get("permalink")
                or item.get("url")
                or item.get("postUrl")
                or ""
            )
            if url and url.startswith("/"):
                url = f"https://www.reddit.com{url}"
            out.append(
                _normalize(
                    source="reddit",
                    title=f"Comment on: {post_title}",
                    snippet=body,
                    url=url,
                    date=_date_from(item.get("createdAt") or item.get("created_utc")),
                    username=_author_from(item),
                    kind="comment",
                )
            )
            continue

        title = item.get("title") or ""
        text = item.get("text") or item.get("selftext") or item.get("body") or ""
        url = item.get("url") or item.get("permalink") or ""
        if url and url.startswith("/"):
            url = f"https://www.reddit.com{url}"
        post_author = _author_from(item)
        out.append(
            _normalize(
                source="reddit",
                title=title,
                snippet=text,
                url=url,
                date=_date_from(item.get("createdAt") or item.get("created_utc")),
                username=post_author,
                kind="post",
            )
        )

        for c in item.get("comments") or []:
            if not isinstance(c, dict):
                continue
            body = c.get("body") or c.get("text") or ""
            if not body.strip():
                continue
            out.append(
                _normalize(
                    source="reddit",
                    title=f"Comment on: {title}" if title else "Reddit comment",
                    snippet=body,
                    url=url,
                    date=_date_from(c.get("createdAt") or c.get("created_utc")),
                    username=_author_from(c),
                    kind="comment",
                )
            )

    return out


# ---------------------------------------------------------------------------
# Instagram — single actor run (posts via profile/name search)
# ---------------------------------------------------------------------------

async def crawl_instagram(client: httpx.AsyncClient, full_name: str) -> List[Dict[str, Any]]:
    """
    One Apify run only — previous version chained 3 sync runs (up to ~5 min).
    """
    settings = get_settings()
    actor = (settings.apify_instagram_actor or DEFAULT_INSTAGRAM_ACTOR).replace("/", "~")
    name = " ".join(full_name.split())

    post_items = await _run_actor(
        client,
        actor,
        {
            "search": name,
            "searchType": "user",
            "resultsType": "posts",
            "resultsLimit": 12,
            "searchLimit": 5,
        },
        timeout_secs=22,
    )

    out: List[Dict[str, Any]] = []
    for item in post_items:
        caption = (
            item.get("caption")
            or item.get("text")
            or item.get("alt")
            or ""
        )
        url = (
            item.get("url")
            or item.get("inputUrl")
            or item.get("displayUrl")
            or ""
        )
        owner = _author_from(item)

        title = f"@{owner}" if owner else "Instagram post"
        out.append(
            _normalize(
                source="instagram",
                title=title,
                snippet=caption,
                url=url,
                date=_date_from(item.get("timestamp") or item.get("takenAt") or item.get("date")),
                username=owner,
                kind="post",
            )
        )

        # Each comment is its own mention (for sighting-claim extraction)
        comments = item.get("latestComments") or item.get("comments") or []
        for c in comments[:12]:
            if isinstance(c, dict):
                t = c.get("text") or c.get("comment") or ""
                c_user = _author_from(c) or (c.get("ownerUsername") or "")
                c_date = _date_from(
                    c.get("timestamp") or c.get("createdAt") or c.get("date")
                )
            elif isinstance(c, str):
                t, c_user, c_date = c, "", ""
            else:
                continue
            if not str(t).strip():
                continue
            out.append(
                _normalize(
                    source="instagram",
                    title=f"Comment on {title}",
                    snippet=str(t),
                    url=url,
                    date=c_date or _date_from(
                        item.get("timestamp") or item.get("takenAt") or item.get("date")
                    ),
                    username=str(c_user).lstrip("@"),
                    kind="comment",
                )
            )

    return out


# ---------------------------------------------------------------------------
# Facebook — public posts / pages search
# ---------------------------------------------------------------------------

async def crawl_facebook(client: httpx.AsyncClient, full_name: str) -> List[Dict[str, Any]]:
    settings = get_settings()
    actor = (settings.apify_facebook_actor or DEFAULT_FACEBOOK_ACTOR).replace("/", "~")
    name = " ".join(full_name.split())

    items = await _run_actor(
        client,
        actor,
        {
            "query": name,
            "resultsCount": 15,
            "searchType": "top",
        },
        timeout_secs=22,
    )

    out: List[Dict[str, Any]] = []
    for item in items:
        text = (
            item.get("text")
            or item.get("message")
            or item.get("postText")
            or item.get("content")
            or ""
        )
        author = _author_from(item)
        title = (
            author
            or item.get("pageName")
            or item.get("title")
            or "Facebook post"
        )
        url = (
            item.get("url")
            or item.get("postUrl")
            or item.get("facebookUrl")
            or item.get("link")
            or ""
        )
        out.append(
            _normalize(
                source="facebook",
                title=str(title),
                snippet=text,
                url=url,
                date=_date_from(
                    item.get("time")
                    or item.get("timestamp")
                    or item.get("date")
                    or item.get("publishedAt")
                ),
                username=author,
                kind="post",
            )
        )
        for c in item.get("comments") or item.get("latestComments") or []:
            if not isinstance(c, dict):
                continue
            body = c.get("text") or c.get("message") or c.get("comment") or ""
            if not str(body).strip():
                continue
            out.append(
                _normalize(
                    source="facebook",
                    title=f"Comment on {title}",
                    snippet=str(body),
                    url=url,
                    date=_date_from(
                        c.get("time") or c.get("timestamp") or c.get("date")
                    ),
                    username=_author_from(c),
                    kind="comment",
                )
            )
    return out


async def collect_apify_mentions(full_name: str) -> Dict[str, Any]:
    """
    Run Reddit + Instagram + Facebook Apify crawlers in parallel.
    Hard-capped so a stuck actor cannot hang Smart Person Search forever.
    """
    if not apify_enabled():
        return {
            "raw_mentions": [],
            "sources_status": {
                "apify_reddit": "skipped (APIFY_TOKEN not configured)",
                "apify_instagram": "skipped (APIFY_TOKEN not configured)",
                "apify_facebook": "skipped (APIFY_TOKEN not configured)",
            },
        }

    async def _run_all() -> Dict[str, Any]:
        timeout = httpx.Timeout(28.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            reddit, instagram, facebook = await asyncio.gather(
                crawl_reddit(client, full_name),
                crawl_instagram(client, full_name),
                crawl_facebook(client, full_name),
                return_exceptions=True,
            )

        raw: List[Dict[str, Any]] = []
        status: Dict[str, str] = {}

        for label, value in (
            ("apify_reddit", reddit),
            ("apify_instagram", instagram),
            ("apify_facebook", facebook),
        ):
            if isinstance(value, Exception):
                status[label] = f"error: {value}"
                continue
            status[label] = f"ok ({len(value)} hits)"
            raw.extend(value)

        return {"raw_mentions": raw, "sources_status": status}

    try:
        return await asyncio.wait_for(_run_all(), timeout=28.0)
    except asyncio.TimeoutError:
        logger.warning("Apify collect timed out after 28s for %r", full_name)
        return {
            "raw_mentions": [],
            "sources_status": {
                "apify_reddit": "error: timed out",
                "apify_instagram": "error: timed out",
                "apify_facebook": "error: timed out",
            },
        }
