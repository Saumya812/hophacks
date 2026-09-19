"""
ElevenLabs TTS — optional. Returns unavailable state when key missing.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent / ".audio_cache"
CACHE_DIR.mkdir(exist_ok=True)


def elevenlabs_configured() -> bool:
    key = get_settings().elevenlabs_api_key or ""
    return bool(key) and not key.upper().startswith("YOUR_")


def synthesize_speech(text: str, *, voice_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert approved public text to audio via ElevenLabs.
    Caches by hash of text+voice on local disk (demo). Prefer object storage in prod.
    """
    settings = get_settings()
    if not elevenlabs_configured():
        return {
            "unavailable": True,
            "provider": "elevenlabs",
            "message": "ELEVENLABS_API_KEY not configured. Transcript-only mode.",
            "transcript": text,
        }

    voice = voice_id or settings.elevenlabs_voice_id or "21m00Tcm4TlvDq8ikWAM"
    digest = hashlib.sha256(f"{voice}:{text}".encode("utf-8")).hexdigest()[:32]
    out_path = CACHE_DIR / f"{digest}.mp3"
    if out_path.exists():
        return {
            "unavailable": False,
            "provider": "elevenlabs",
            "cached": True,
            "audio_path": str(out_path),
            "audio_url": f"/audio/{digest}.mp3",
            "transcript": text,
            "voice_id": voice,
        }

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                headers={
                    "xi-api-key": settings.elevenlabs_api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": text[:2500],
                    "model_id": settings.elevenlabs_model or "eleven_monolingual_v1",
                },
            )
            if resp.status_code != 200:
                return {
                    "unavailable": True,
                    "provider": "elevenlabs",
                    "message": f"ElevenLabs error HTTP {resp.status_code}",
                    "transcript": text,
                }
            out_path.write_bytes(resp.content)
        return {
            "unavailable": False,
            "provider": "elevenlabs",
            "cached": False,
            "audio_url": f"/audio/{digest}.mp3",
            "transcript": text,
            "voice_id": voice,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("ElevenLabs failed: %s", exc)
        return {
            "unavailable": True,
            "provider": "elevenlabs",
            "message": str(exc),
            "transcript": text,
        }
