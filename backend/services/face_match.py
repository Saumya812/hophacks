"""
Face recognition matching against active case profile photos.

Engines (first available wins per comparison strategy):
1. AWS Rekognition CompareFaces — if AWS credentials configured
2. DeepFace (Facenet) — if the deepface package is installed
3. Gemini Vision — if GEMINI_API_KEY is configured (labeled as vision assist)

Returns similarity scores 0–100 and a short match list for the demo UX:
"This person may match N active cases".
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from config import get_settings
from database import get_supabase
from services.gemini_client import gemini_configured, get_generative_model

logger = logging.getLogger(__name__)

USER_AGENT = "FindMyPalFaceMatch/1.0"


def _decode_photo(photo: str) -> bytes:
    raw = (photo or "").strip()
    if raw.startswith("data:image"):
        raw = raw.split(",", 1)[1]
    return base64.b64decode(raw)


def _engine_availability() -> Dict[str, bool]:
    settings = get_settings()
    aws = bool(
        (settings.aws_access_key_id or "")
        and (settings.aws_secret_access_key or "")
        and not settings.aws_access_key_id.upper().startswith("YOUR_")
    )
    deepface = False
    try:
        import deepface  # noqa: F401

        deepface = True
    except Exception:  # noqa: BLE001
        deepface = False
    return {
        "aws_rekognition": aws,
        "deepface": deepface,
        "gemini_vision": gemini_configured(),
    }


def _download_image(url: str) -> Optional[bytes]:
    if not url:
        return None
    try:
        if url.startswith("data:image"):
            return _decode_photo(url)
        with httpx.Client(timeout=20.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            r = client.get(url)
            if r.status_code == 200 and r.content:
                return r.content
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to download photo %s: %s", url[:80], exc)
    return None


def _compare_rekognition(probe: bytes, candidate: bytes) -> Optional[float]:
    settings = get_settings()
    try:
        import boto3

        client = boto3.client(
            "rekognition",
            region_name=settings.aws_region or "us-east-1",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        resp = client.compare_faces(
            SourceImage={"Bytes": probe},
            TargetImage={"Bytes": candidate},
            SimilarityThreshold=50,
        )
        matches = resp.get("FaceMatches") or []
        if not matches:
            return 0.0
        return float(matches[0]["Similarity"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Rekognition compare failed: %s", exc)
        return None


def _compare_deepface(probe: bytes, candidate: bytes) -> Optional[float]:
    try:
        from deepface import DeepFace

        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "probe.jpg"
            b = Path(tmp) / "cand.jpg"
            a.write_bytes(probe)
            b.write_bytes(candidate)
            result = DeepFace.verify(
                img1_path=str(a),
                img2_path=str(b),
                model_name="Facenet",
                enforce_detection=False,
                silent=True,
            )
            # distance → similarity heuristic
            distance = float(result.get("distance") or 1.0)
            threshold = float(result.get("threshold") or 0.4)
            # Map distance to 0–100 (lower distance = higher similarity)
            sim = max(0.0, min(100.0, (1.0 - (distance / max(threshold * 2, 1e-6))) * 100.0))
            if result.get("verified"):
                sim = max(sim, 75.0)
            return sim
    except Exception as exc:  # noqa: BLE001
        logger.warning("DeepFace compare failed: %s", exc)
        return None


def _compare_gemini_vision(probe: bytes, candidate: bytes) -> Optional[float]:
    if not gemini_configured():
        return None
    try:
        import google.generativeai as genai

        model = get_generative_model(
            system_instruction=(
                "You compare two photos for possible same-person identity for a "
                "missing-persons tip tool. Return ONLY JSON: "
                '{"similarity": 0-100 integer, "same_person_likely": true/false, "reason": "short"}'
            )
        )
        probe_part = {"mime_type": "image/jpeg", "data": probe}
        cand_part = {"mime_type": "image/jpeg", "data": candidate}
        resp = model.generate_content(
            [
                "Photo A is a probe upload. Photo B is an active missing-person profile photo. "
                "Estimate visual similarity for identity matching.",
                probe_part,
                cand_part,
            ],
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"},
        )
        text = getattr(resp, "text", "") or ""
        data = json.loads(text)
        return float(data.get("similarity", 0))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini vision compare failed: %s", exc)
        return None


def compare_faces(probe: bytes, candidate: bytes, preferred_engine: Optional[str] = None) -> Tuple[float, str]:
    """
    Compare two face images. Returns (similarity_0_100, engine_used).
    """
    avail = _engine_availability()
    order = []
    if preferred_engine:
        order.append(preferred_engine)
    order.extend(["aws_rekognition", "deepface", "gemini_vision"])

    seen = set()
    for eng in order:
        if eng in seen:
            continue
        seen.add(eng)
        if not avail.get(eng):
            continue
        if eng == "aws_rekognition":
            score = _compare_rekognition(probe, candidate)
        elif eng == "deepface":
            score = _compare_deepface(probe, candidate)
        else:
            score = _compare_gemini_vision(probe, candidate)
        if score is not None:
            return score, eng

    raise RuntimeError(
        "No face-matching engine available. Install deepface, configure AWS Rekognition, "
        "or set GEMINI_API_KEY for vision assist."
    )


def match_probe_against_active_cases(
    photo_b64: str,
    *,
    min_similarity: float = 55.0,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Compare an uploaded probe photo to all active cases that have photo_url.
    """
    probe = _decode_photo(photo_b64)
    if len(probe) < 100:
        raise ValueError("Photo payload too small")

    avail = _engine_availability()
    if not any(avail.values()):
        return {
            "engine": None,
            "engines_available": avail,
            "match_count": 0,
            "message": "Face matching unavailable — configure DeepFace, AWS Rekognition, or Gemini.",
            "matches": [],
            "unavailable": True,
        }

    supabase = get_supabase()
    result = (
        supabase.table("persons")
        .select("*")
        .eq("status", "active")
        .not_.is_("photo_url", "null")
        .execute()
    )
    rows = [r for r in (result.data or []) if r.get("photo_url")]

    matches: List[Dict[str, Any]] = []
    engine_used = None
    errors = 0

    for row in rows:
        cand_bytes = _download_image(row["photo_url"])
        if not cand_bytes:
            continue
        try:
            score, engine_used = compare_faces(probe, cand_bytes)
        except Exception:  # noqa: BLE001
            errors += 1
            continue
        if score >= min_similarity:
            matches.append(
                {
                    "person_id": row["id"],
                    "name": row.get("name"),
                    "age": row.get("age"),
                    "last_seen_location": row.get("last_seen_location"),
                    "photo_url": row.get("photo_url"),
                    "similarity": round(score, 1),
                    "status": row.get("status"),
                }
            )

    matches.sort(key=lambda m: m["similarity"], reverse=True)
    matches = matches[:limit]
    n = len(matches)
    if n == 0:
        message = "No strong matches among active cases with photos."
    elif n == 1:
        message = "This person may match 1 active case"
    else:
        message = f"This person may match {n} active cases"

    return {
        "engine": engine_used,
        "engines_available": avail,
        "match_count": n,
        "message": message,
        "matches": matches,
        "candidates_scanned": len(rows),
        "compare_errors": errors,
        "unavailable": False,
    }
