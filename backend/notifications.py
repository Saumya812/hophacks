"""
Police / family tip notifications via EmailJS (additive — optional env).

When EmailJS env vars are missing, calls no-op and return False so tip
submission still succeeds.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

import httpx

EMAILJS_URL = "https://api.emailjs.com/api/v1.0/email/send"


def _emailjs_ready() -> bool:
    return bool(
        os.getenv("EMAILJS_SERVICE_ID")
        and os.getenv("EMAILJS_PUBLIC_KEY")
    )


async def _send_emailjs(template_id: str | None, params: Dict[str, Any]) -> bool:
    if not _emailjs_ready() or not template_id:
        print("EmailJS not configured — skipping notification")
        return False

    payload = {
        "service_id": os.getenv("EMAILJS_SERVICE_ID"),
        "template_id": template_id,
        "user_id": os.getenv("EMAILJS_PUBLIC_KEY"),
        "template_params": params,
    }
    # Optional private key for EmailJS REST (if account requires it)
    private = os.getenv("EMAILJS_PRIVATE_KEY")
    if private:
        payload["accessToken"] = private

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(EMAILJS_URL, json=payload, timeout=10.0)
            if response.status_code != 200:
                print(f"EmailJS error {response.status_code}: {response.text[:200]}")
                return False
            return True
    except Exception as exc:
        print(f"Notification failed: {exc}")
        return False


async def notify_police_new_tip(person: dict, tip: dict) -> bool:
    """
    Sends notification when a new tip is submitted.
    Uses EmailJS REST API (free tier; no SMTP required).
    """
    tip_details = f"""
NEW TIP SUBMITTED — FindMyPal

MISSING PERSON: {person.get('name')}
Age: {person.get('age', 'Unknown')}
Last seen: {person.get('last_seen_location', 'Unknown')}
Case ID: {person.get('id')}

TIP DETAILS:
Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Type: {tip.get('tip_type', 'General')}
Location reported: {tip.get('location', tip.get('location_text', 'Not specified'))}
When seen: {tip.get('seen_at', tip.get('date_time', 'Not specified'))}
Confidence: {tip.get('confidence_level', 'Unknown')}

Description:
{tip.get('description', 'No description provided')}

Submitter contact: {tip.get('submitter_email', 'Anonymous')}

View case: https://findmypal.app/person/{person.get('id')}

To mark this person as FOUND, POST /persons/{{id}}/verify-found
with code starting with POLICE-.
""".strip()

    return await _send_emailjs(
        os.getenv("EMAILJS_TEMPLATE_ID"),
        {
            "to_email": os.getenv(
                "POLICE_NOTIFICATION_EMAIL", "demo-police@findmypal.app"
            ),
            "case_id": str(person.get("id")),
            "person_name": person.get("name") or "Unknown",
            "tip_summary": tip_details,
            "case_url": f"https://findmypal.app/person/{person.get('id')}",
        },
    )


async def notify_family_new_tip(person: dict, tip: dict) -> bool:
    """Sends notification to case creator when a new tip arrives."""
    email = person.get("contact_email")
    if not email:
        return False

    return await _send_emailjs(
        os.getenv("EMAILJS_FAMILY_TEMPLATE_ID"),
        {
            "to_email": email,
            "person_name": person.get("name") or "Unknown",
            "tip_location": tip.get(
                "location", tip.get("location_text", "Not specified")
            ),
            "tip_description": tip.get("description", ""),
            "confidence": str(tip.get("confidence_level", "Unknown")),
            "case_url": f"https://findmypal.app/person/{person.get('id')}",
        },
    )


def notify_police_new_tip_sync(person: dict, tip: dict) -> bool:
    """Sync wrapper for FastAPI sync routes."""
    import asyncio

    try:
        return asyncio.run(notify_police_new_tip(person, tip))
    except RuntimeError:
        # Already in an event loop — schedule best-effort
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(notify_police_new_tip(person, tip))
                return True
        except Exception:
            pass
        return False


def notify_family_new_tip_sync(person: dict, tip: dict) -> bool:
    import asyncio

    try:
        return asyncio.run(notify_family_new_tip(person, tip))
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(notify_family_new_tip(person, tip))
                return True
        except Exception:
            pass
        return False
