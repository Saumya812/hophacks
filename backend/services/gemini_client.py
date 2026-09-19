"""
Shared Gemini helpers — resolve a working model ID and configure the client.

Prefer current flash models (gemini-3.6-flash+). Older 2.5 IDs may still
appear in ListModels but return 404 for new API keys.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional, Set

import google.generativeai as genai

from config import get_settings

logger = logging.getLogger(__name__)

# Prefer models that work for new AI Studio keys (3.6+). Include lites for
# separate free-tier quotas when the primary is rate-limited.
_MODEL_CANDIDATES: List[str] = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.6-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash",
]

_resolved: Optional[str] = None
_cooldown: dict[str, float] = {}  # model -> retry_after monotonic
_unavailable: Set[str] = set()  # hard 404 / not available to new users


def gemini_configured() -> bool:
    key = get_settings().gemini_api_key or ""
    return bool(key) and not key.upper().startswith("YOUR_")


def configure_gemini() -> None:
    if not gemini_configured():
        raise RuntimeError("GEMINI_API_KEY is not configured")
    genai.configure(api_key=get_settings().gemini_api_key)


def _list_generate_models() -> Set[str]:
    available: Set[str] = set()
    for m in genai.list_models():
        methods = getattr(m, "supported_generation_methods", []) or []
        if "generateContent" in methods:
            name = getattr(m, "name", "") or ""
            available.add(name.split("/")[-1])
    return available


def resolve_gemini_model(*, force: bool = False) -> str:
    """
    Pick a generateContent model from our preferred list.
    Never use alphabetical ListModels fallback.
    """
    global _resolved
    if _resolved and not force and _resolved not in _unavailable:
        until = _cooldown.get(_resolved, 0.0)
        if until <= time.monotonic():
            return _resolved

    configure_gemini()
    preferred = (get_settings().gemini_model or "").strip()
    candidates = ([preferred] if preferred else []) + _MODEL_CANDIDATES

    try:
        available = _list_generate_models()
    except Exception as exc:  # noqa: BLE001
        logger.warning("list_models failed (%s); trying candidates blindly", exc)
        available = set()

    now = time.monotonic()
    for cand in candidates:
        if not cand or cand in _unavailable:
            continue
        if available and cand not in available:
            continue
        until = _cooldown.get(cand, 0.0)
        if until > now:
            continue
        _resolved = cand
        logger.info("Using Gemini model %s", cand)
        return cand

    # Last resort: preferred or first candidate (even if not listed)
    _resolved = preferred or _MODEL_CANDIDATES[0]
    logger.info("Using Gemini model %s (fallback)", _resolved)
    return _resolved


def mark_model_rate_limited(model_name: str, retry_after_secs: float = 45.0) -> None:
    """Temporarily skip a model after a 429 so we rotate to another."""
    global _resolved
    _cooldown[model_name] = time.monotonic() + max(5.0, retry_after_secs)
    if _resolved == model_name:
        _resolved = None
    logger.warning(
        "Gemini model %s rate-limited; cooling down %.0fs",
        model_name,
        retry_after_secs,
    )


def mark_model_unavailable(model_name: str) -> None:
    """Permanently skip a model for this process (404 / not available to new users)."""
    global _resolved
    _unavailable.add(model_name)
    if _resolved == model_name:
        _resolved = None
    logger.warning("Gemini model %s marked unavailable for this process", model_name)


def get_generative_model(
    system_instruction: Optional[str] = None,
    *,
    model_name: Optional[str] = None,
):
    """Return a GenerativeModel with a resolved (or explicit) model id."""
    configure_gemini()
    name = model_name or resolve_gemini_model()
    kwargs = {"model_name": name}
    if system_instruction:
        kwargs["system_instruction"] = system_instruction
    return genai.GenerativeModel(**kwargs)


def iter_model_fallbacks(primary: Optional[str] = None) -> List[str]:
    """Ordered unique model ids to try on failure (only ListModels-available when possible)."""
    preferred = (get_settings().gemini_model or "").strip()
    primary = primary or resolve_gemini_model()
    try:
        available = _list_generate_models()
    except Exception:  # noqa: BLE001
        available = set()

    seen: Set[str] = set()
    out: List[str] = []
    now = time.monotonic()
    for cand in [primary, preferred, *_MODEL_CANDIDATES]:
        if not cand or cand in seen or cand in _unavailable:
            continue
        if available and cand not in available:
            continue
        if _cooldown.get(cand, 0.0) > now:
            continue
        seen.add(cand)
        out.append(cand)
    return out
