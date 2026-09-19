"""
Smart Person Search — public-web scraper service.

Runs SerpAPI / Reddit / NewsAPI / Twitter / YouTube (and Google site:
operators for IG/FB/TikTok) in parallel via asyncio + httpx.

When APIFY_TOKEN is set, also runs Apify crawlers for:
  - Reddit posts + comments
  - Instagram posts + comments
  - Facebook public posts/pages

Sources with missing API keys are skipped gracefully so the feature still
works in demo mode with whatever keys are configured.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from config import get_settings
from services.apify_crawlers import apify_enabled, collect_apify_mentions
from services.gemini_processor import filter_raw_mentions_for_person, mention_matches_person

logger = logging.getLogger(__name__)

USER_AGENT = "FindMyPalLookup/1.0 (missing-persons research; contact: mock@findmypal.local)"


def _configured(value: Optional[str]) -> bool:
    """True when an env value looks like a real key (not a placeholder)."""
    if not value:
        return False
    upper = value.upper()
    return not upper.startswith("YOUR_") and "PLACEHOLDER" not in upper and len(value) > 8


def _normalize_result(
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
    """Uniform raw-mention shape before Gemini processing."""
    text = " ".join(part for part in [title, snippet] if part).strip()
    return {
        "source": source,
        "title": (title or "")[:300],
        "snippet": (snippet or text)[:1000],
        "text": text[:2000],
        "url": url or "",
        "date": date or "",
        "username": (username or "").lstrip("@")[:80],
        "kind": (kind or "post")[:40],
        "time": (time or "")[:40],
    }


# ---------------------------------------------------------------------------
# Individual source fetchers
# ---------------------------------------------------------------------------

async def _serp_search(client: httpx.AsyncClient, query: str, num: int = 20) -> List[Dict[str, Any]]:
    """Google results via SerpAPI, or DuckDuckGo HTML fallback when no key."""
    settings = get_settings()
    results: List[Dict[str, Any]] = []

    if _configured(settings.serpapi_key):
        try:
            resp = await client.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google",
                    "q": query,
                    "num": min(num, 20),
                    "api_key": settings.serpapi_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            for item in (data.get("organic_results") or [])[:num]:
                results.append(
                    _normalize_result(
                        source=_guess_platform(item.get("link", ""), "google"),
                        title=item.get("title", ""),
                        snippet=item.get("snippet", ""),
                        url=item.get("link", ""),
                        date=item.get("date", "") or "",
                    )
                )
            return results
        except Exception as exc:  # noqa: BLE001
            logger.warning("SerpAPI failed for %r: %s", query, exc)

    # Free fallback so hackathon demos still return something without SerpAPI
    try:
        resp = await client.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={"User-Agent": USER_AGENT},
        )
        if resp.status_code == 200:
            html = resp.text
            # Lightweight parse of DDG result blocks
            blocks = re.findall(
                r'uddg=([^&"]+).*?result__a[^>]*>(.*?)</a>.*?result__snippet[^>]*>(.*?)</',
                html,
                flags=re.I | re.S,
            )
            if not blocks:
                blocks = re.findall(
                    r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                    html,
                    flags=re.I | re.S,
                )
                for href, title in blocks[:num]:
                    results.append(
                        _normalize_result(
                            source=_guess_platform(href, "web"),
                            title=re.sub(r"<[^>]+>", "", title),
                            snippet="",
                            url=href,
                        )
                    )
            else:
                from urllib.parse import unquote

                for href, title, snippet in blocks[:num]:
                    url = unquote(href)
                    results.append(
                        _normalize_result(
                            source=_guess_platform(url, "web"),
                            title=re.sub(r"<[^>]+>", "", title),
                            snippet=re.sub(r"<[^>]+>", "", snippet),
                            url=url,
                        )
                    )
    except Exception as exc:  # noqa: BLE001
        logger.warning("DuckDuckGo fallback failed for %r: %s", query, exc)

    return results


def _guess_platform(url: str, default: str = "web") -> str:
    """Map a URL host to a friendly platform label."""
    host = (urlparse(url).netloc or "").lower()
    mapping = [
        ("instagram.com", "instagram"),
        ("facebook.com", "facebook"),
        ("fb.com", "facebook"),
        ("tiktok.com", "tiktok"),
        ("twitter.com", "x"),
        ("x.com", "x"),
        ("reddit.com", "reddit"),
        ("youtube.com", "youtube"),
        ("youtu.be", "youtube"),
        ("news", "news"),
    ]
    for needle, label in mapping:
        if needle in host:
            return label
    return default


async def search_google_queries(client: httpx.AsyncClient, full_name: str) -> List[Dict[str, Any]]:
    """SerpAPI / web search — quoted full name only (no bare 'seen' keyword noise)."""
    queries = [
        f'"{full_name}" missing',
        f'"{full_name}" "missing person"',
        f'"{full_name}" "last seen"',
        f'"{full_name}"',
        f'site:instagram.com "{full_name}"',
        f'site:facebook.com "{full_name}"',
        f'site:tiktok.com "{full_name}"',
        f'site:youtube.com "{full_name}"',
        f'site:reddit.com "{full_name}"',
        f'site:news.google.com "{full_name}" missing',
    ]
    batches = await asyncio.gather(
        *[_serp_search(client, q, num=20) for q in queries],
        return_exceptions=True,
    )
    out: List[Dict[str, Any]] = []
    for batch in batches:
        if isinstance(batch, Exception):
            logger.warning("Google batch error: %s", batch)
            continue
        out.extend(batch)
    return out


async def search_reddit(client: httpx.AsyncClient, full_name: str) -> List[Dict[str, Any]]:
    """
    Reddit public search JSON.

    Pushshift is largely unavailable; Reddit's public search endpoint is used
    as the free replacement called out in the feature brief.
    """
    results: List[Dict[str, Any]] = []
    try:
        resp = await client.get(
            "https://www.reddit.com/search.json",
            params={"q": full_name, "limit": 25, "sort": "relevance", "t": "all"},
            headers={"User-Agent": USER_AGENT},
        )
        if resp.status_code != 200:
            return results
        children = (resp.json().get("data") or {}).get("children") or []
        for child in children:
            data = child.get("data") or {}
            title = data.get("title") or ""
            body = data.get("selftext") or ""
            permalink = data.get("permalink") or ""
            url = f"https://www.reddit.com{permalink}" if permalink else data.get("url", "")
            created = data.get("created_utc")
            date = ""
            if created:
                from datetime import datetime, timezone

                date = datetime.fromtimestamp(float(created), tz=timezone.utc).strftime("%Y-%m-%d")
            results.append(
                _normalize_result(
                    source="reddit",
                    title=title,
                    snippet=body[:500],
                    url=url,
                    date=date,
                )
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Reddit search failed: %s", exc)
    return results


async def search_newsapi(client: httpx.AsyncClient, full_name: str) -> List[Dict[str, Any]]:
    """NewsAPI everything search (skipped when NEWSAPI_KEY missing)."""
    settings = get_settings()
    if not _configured(settings.newsapi_key):
        return []

    results: List[Dict[str, Any]] = []
    try:
        resp = await client.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": f'"{full_name}"',
                "pageSize": 20,
                "language": "en",
                "sortBy": "relevancy",
                "apiKey": settings.newsapi_key,
            },
        )
        if resp.status_code != 200:
            logger.warning("NewsAPI status %s: %s", resp.status_code, resp.text[:200])
            return results
        for article in (resp.json().get("articles") or [])[:20]:
            results.append(
                _normalize_result(
                    source="news",
                    title=article.get("title") or "",
                    snippet=article.get("description") or article.get("content") or "",
                    url=article.get("url") or "",
                    date=(article.get("publishedAt") or "")[:10],
                )
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("NewsAPI failed: %s", exc)
    return results


async def search_twitter(client: httpx.AsyncClient, full_name: str) -> List[Dict[str, Any]]:
    """
    Twitter/X via RapidAPI twitter scraper (optional).

    Also falls back to Google site:x.com / site:twitter.com via SerpAPI path.
    """
    settings = get_settings()
    results: List[Dict[str, Any]] = []

    if _configured(settings.rapidapi_key) and _configured(settings.twitter_rapidapi_host):
        try:
            resp = await client.get(
                f"https://{settings.twitter_rapidapi_host}/search",
                params={"query": full_name, "section": "latest", "limit": "20"},
                headers={
                    "X-RapidAPI-Key": settings.rapidapi_key,
                    "X-RapidAPI-Host": settings.twitter_rapidapi_host,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                # Shape varies by provider — handle common patterns
                tweets = data if isinstance(data, list) else (
                    data.get("data")
                    or data.get("tweets")
                    or data.get("results")
                    or []
                )
                for tw in tweets[:20]:
                    if not isinstance(tw, dict):
                        continue
                    text = tw.get("text") or tw.get("full_text") or tw.get("content") or ""
                    url = tw.get("url") or tw.get("tweet_url") or ""
                    if not url and tw.get("id"):
                        url = f"https://x.com/i/web/status/{tw['id']}"
                    results.append(
                        _normalize_result(
                            source="x",
                            title="",
                            snippet=text,
                            url=url,
                            date=(tw.get("created_at") or tw.get("date") or "")[:10],
                        )
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Twitter RapidAPI failed: %s", exc)

    # Always try indexed tweets via Google operators as well
    site_hits = await asyncio.gather(
        _serp_search(client, f'site:twitter.com "{full_name}"', num=10),
        _serp_search(client, f'site:x.com "{full_name}"', num=10),
        return_exceptions=True,
    )
    for batch in site_hits:
        if isinstance(batch, list):
            for item in batch:
                item["source"] = "x"
                results.append(item)

    return results


async def search_youtube(client: httpx.AsyncClient, full_name: str) -> List[Dict[str, Any]]:
    """
    YouTube mentions via (in order):
      1. YouTube Data API v3 (if YOUTUBE_API_KEY set)
      2. SerpAPI YouTube engine (if SERPAPI_KEY set)
      3. Google site:youtube.com SerpAPI fallback

    Every result is name-filtered — bare 'missing person' shorts must not leak in.
    """
    settings = get_settings()
    name = " ".join(full_name.split())
    results: List[Dict[str, Any]] = []

    def _keep(item: Dict[str, Any]) -> bool:
        return mention_matches_person(name, item)

    # --- 1) Official YouTube Data API ---
    if _configured(settings.youtube_api_key):
        try:
            resp = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": f'"{name}"',
                    "type": "video",
                    "maxResults": 15,
                    "key": settings.youtube_api_key,
                },
            )
            if resp.status_code == 200:
                items = resp.json().get("items") or []
                video_ids = []
                for item in items:
                    sn = item.get("snippet") or {}
                    vid = (item.get("id") or {}).get("videoId") or ""
                    if vid:
                        video_ids.append(vid)
                    row = _normalize_result(
                        source="youtube",
                        title=sn.get("title") or "",
                        snippet=sn.get("description") or "",
                        url=f"https://www.youtube.com/watch?v={vid}" if vid else "",
                        date=(sn.get("publishedAt") or "")[:10],
                    )
                    if _keep(row):
                        results.append(row)

                async def _comments(video_id: str) -> List[Dict[str, Any]]:
                    try:
                        cr = await client.get(
                            "https://www.googleapis.com/youtube/v3/commentThreads",
                            params={
                                "part": "snippet",
                                "videoId": video_id,
                                "maxResults": 5,
                                "order": "relevance",
                                "textFormat": "plainText",
                                "key": settings.youtube_api_key,
                            },
                        )
                        if cr.status_code != 200:
                            return []
                        out = []
                        for thread in cr.json().get("items") or []:
                            top = (
                                ((thread.get("snippet") or {}).get("topLevelComment") or {}).get(
                                    "snippet"
                                )
                                or {}
                            )
                            row = _normalize_result(
                                source="youtube",
                                title="Comment",
                                snippet=top.get("textDisplay") or "",
                                url=f"https://www.youtube.com/watch?v={video_id}",
                                date=(top.get("publishedAt") or "")[:10],
                            )
                            if _keep(row):
                                out.append(row)
                        return out
                    except Exception:  # noqa: BLE001
                        return []

                comment_batches = await asyncio.gather(
                    *[_comments(vid) for vid in video_ids[:5]],
                    return_exceptions=True,
                )
                for batch in comment_batches:
                    if isinstance(batch, list):
                        results.extend(batch)
                if results:
                    return results[:25]
            else:
                logger.warning("YouTube Data API status %s: %s", resp.status_code, resp.text[:200])
        except Exception as exc:  # noqa: BLE001
            logger.warning("YouTube Data API failed: %s", exc)

    # --- 2) SerpAPI native YouTube engine ---
    if _configured(settings.serpapi_key):
        queries = [f'"{name}"', f'"{name}" missing', f'"{name}" "last seen"']
        for q in queries:
            try:
                resp = await client.get(
                    "https://serpapi.com/search.json",
                    params={
                        "engine": "youtube",
                        "search_query": q,
                        "api_key": settings.serpapi_key,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("video_results") or []:
                    link = item.get("link") or ""
                    if not link:
                        vid = item.get("video_id") or ""
                        link = f"https://www.youtube.com/watch?v={vid}" if vid else ""
                    row = _normalize_result(
                        source="youtube",
                        title=item.get("title") or "",
                        snippet=item.get("description") or "",
                        url=link,
                        date=item.get("published_date") or "",
                    )
                    if _keep(row):
                        results.append(row)
                for block in data.get("shorts_results") or []:
                    for short in block.get("shorts") or []:
                        link = short.get("link") or ""
                        vid = short.get("video_id") or ""
                        if not link and vid:
                            link = f"https://www.youtube.com/shorts/{vid}"
                        row = _normalize_result(
                            source="youtube",
                            title=short.get("title") or "YouTube Short",
                            snippet="",
                            url=link,
                            date="",
                        )
                        if _keep(row):
                            results.append(row)
            except Exception as exc:  # noqa: BLE001
                logger.warning("SerpAPI YouTube engine failed for %r: %s", q, exc)

        if results:
            seen = set()
            uniq = []
            for item in results:
                key = (item.get("url") or "").split("?")[0]
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                uniq.append(item)
            return uniq[:25]

    # --- 3) Google site: fallback ---
    for q in (
        f'site:youtube.com "{name}"',
        f'site:youtu.be "{name}"',
        f'site:youtube.com "{name}" missing',
    ):
        batch = await _serp_search(client, q, num=15)
        for item in batch:
            item = dict(item)
            item["source"] = "youtube"
            if _keep(item):
                results.append(item)
        if results:
            break

    return results[:25]


def _dedupe_raw(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop duplicate URLs / near-identical snippets. Prefer platform-tagged sources."""
    prefer = {
        "youtube": 3,
        "instagram": 3,
        "facebook": 3,
        "reddit": 3,
        "tiktok": 3,
        "x": 2,
        "twitter": 2,
        "news": 2,
        "google": 1,
        "web": 0,
    }
    best: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    seen_text = set()

    for item in items:
        url = (item.get("url") or "").split("#")[0].split("?")[0].rstrip("/")
        text_key = re.sub(r"\s+", " ", (item.get("text") or item.get("snippet") or "").lower())[:160]
        src = (item.get("source") or "web").lower()
        score = prefer.get(src, 0)

        if url:
            prev = best.get(url)
            if prev is None:
                best[url] = item
                order.append(url)
            else:
                prev_score = prefer.get((prev.get("source") or "web").lower(), 0)
                if score > prev_score:
                    best[url] = item
            continue

        if text_key and text_key in seen_text:
            continue
        if text_key:
            seen_text.add(text_key)
        # URL-less items keep insertion order via synthetic key
        key = f"text:{len(order)}:{text_key[:40]}"
        best[key] = item
        order.append(key)

    return [best[k] for k in order if k in best]


async def collect_raw_mentions(full_name: str) -> Dict[str, Any]:
    """
    Run all search sources in parallel and return raw mentions + source status.
    """
    name = " ".join(full_name.split())
    sources_status: Dict[str, str] = {}
    settings = get_settings()
    use_apify = apify_enabled()

    timeout = httpx.Timeout(20.0, connect=8.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        tasks = [
            search_google_queries(client, name),
            search_newsapi(client, name),
            search_twitter(client, name),
            search_youtube(client, name),
            search_reddit(client, name),
        ]
        apify_coro = collect_apify_mentions(name) if use_apify else None
        if apify_coro is not None:
            gathered = await asyncio.gather(*tasks, apify_coro, return_exceptions=True)
            base, apify_bundle = gathered[:-1], gathered[-1]
        else:
            base = await asyncio.gather(*tasks, return_exceptions=True)
            apify_bundle = {"raw_mentions": [], "sources_status": {}}

    google, news, twitter, youtube, reddit_public = base

    raw: List[Dict[str, Any]] = []

    def _absorb(label: str, value: Any, *, needs_key: bool = False, key_ok: bool = True) -> None:
        if isinstance(value, Exception):
            sources_status[label] = f"error: {value}"
            return
        if needs_key and not key_ok and not value:
            sources_status[label] = "skipped (API key not configured)"
            return
        if not isinstance(value, list):
            sources_status[label] = "skipped"
            return
        sources_status[label] = f"ok ({len(value)} hits)"
        raw.extend(value)

    _absorb("google_and_social_index", google)
    _absorb("newsapi", news, needs_key=True, key_ok=_configured(settings.newsapi_key))
    _absorb("twitter_x", twitter)
    _absorb("youtube", youtube)
    _absorb("reddit_public", reddit_public)

    if use_apify:
        if isinstance(apify_bundle, Exception):
            sources_status["apify"] = f"error: {apify_bundle}"
        else:
            sources_status.update((apify_bundle or {}).get("sources_status") or {})
            raw.extend((apify_bundle or {}).get("raw_mentions") or [])
    else:
        sources_status.setdefault("apify_reddit", "skipped (APIFY_TOKEN not configured)")
        sources_status.setdefault("apify_instagram", "skipped (APIFY_TOKEN not configured)")
        sources_status.setdefault("apify_facebook", "skipped (APIFY_TOKEN not configured)")

    raw = _dedupe_raw(raw)
    raw = filter_raw_mentions_for_person(name, raw)
    return {
        "full_name": name,
        "raw_mentions": raw,
        "sources_status": sources_status,
        "raw_count": len(raw),
    }
