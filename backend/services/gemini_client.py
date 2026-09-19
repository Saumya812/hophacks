"""
Shared Gemini helpers — resolve a working model ID and configure the client.

S0 found that hard-coded gemini-1.5-flash 404s on some API keys; we probe
candidates once per process.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import List, Optional

import google.generativeai as genai

from config import get_settings

logger = logging.getLogger(__name__)

# Prefer newer flash models; keep older names as fallbacks.
_MODEL_CANDIDATES: List[str] = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-flash-latest",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash",
    "gemini-pro",
]


def gemini_configured() -> bool:
    key = get_settings().gemini_api_key or ""
    return bool(key) and not key.upper().startswith("YOUR_")


def configure_gemini() -> None:
    if not gemini_configured():
        raise RuntimeError("GEMINI_API_KEY is not configured")
    genai.configure(api_key=get_settings().gemini_api_key)


@lru_cache
def resolve_gemini_model() -> str:
    """
    Pick the first model that ListModels reports as supporting generateContent.
    Falls back to the first candidate if listing fails.
    """
    configure_gemini()
    preferred = (get_settings().gemini_model or "").strip()
    candidates = ([preferred] if preferred else []) + _MODEL_CANDIDATES

    try:
        available = set()
        for m in genai.list_models():
            methods = getattr(m, "supported_generation_methods", []) or []
            if "generateContent" in methods:
                # names look like models/gemini-2.0-flash
                name = getattr(m, "name", "") or ""
                available.add(name.split("/")[-1])
        for cand in candidates:
            if cand and cand in available:
                logger.info("Using Gemini model %s", cand)
                return cand
        if available:
            pick = sorted(available)[0]
            logger.info("Using first listed Gemini model %s", pick)
            return pick
    except Exception as exc:  # noqa: BLE001
        logger.warning("list_models failed (%s); trying candidates blindly", exc)

    return preferred or _MODEL_CANDIDATES[0]


def get_generative_model(system_instruction: Optional[str] = None):
    """Return a GenerativeModel with a resolved model id."""
    configure_gemini()
    model_name = resolve_gemini_model()
    kwargs = {"model_name": model_name}
    if system_instruction:
        kwargs["system_instruction"] = system_instruction
    return genai.GenerativeModel(**kwargs)
