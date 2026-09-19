"""Focused checks for person source URL validation (stdlib unittest, no pytest required)."""
from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from uuid import uuid4

from pydantic import ValidationError

from schemas import PersonCreate, PersonOut


def _base(**over):
    data = {
        "name": "Test Person",
        "age": 30,
        "last_seen_location": "Baltimore, MD",
        "last_seen_date": date(2024, 1, 15),
        "description": "Test description for validation.",
    }
    data.update(over)
    return data


class TestSourceFields(unittest.TestCase):
    def test_source_listing_url_https_ok(self):
        p = PersonCreate(**_base(source_listing_url="https://agency.example/case/1?ref=abc"))
        self.assertTrue(p.source_listing_url.startswith("https://"))
        self.assertIn("ref=abc", p.source_listing_url)

    def test_source_listing_url_rejects_javascript(self):
        with self.assertRaises(ValidationError):
            PersonCreate(**_base(source_listing_url="javascript:alert(1)"))

    def test_source_listing_url_optional_empty(self):
        p = PersonCreate(**_base(source_listing_url=""))
        self.assertIsNone(p.source_listing_url)

    def test_external_case_separate_from_police(self):
        p = PersonCreate(
            **_base(police_report_number="PD-111", external_case_number="NAMUS-999")
        )
        self.assertEqual(p.police_report_number, "PD-111")
        self.assertEqual(p.external_case_number, "NAMUS-999")

    def test_person_out_without_source_fields(self):
        out = PersonOut(
            id=uuid4(),
            name="Legacy",
            age=40,
            last_seen_location="Annapolis, MD",
            last_seen_date=date(2023, 5, 1),
            description="Legacy case",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        self.assertIsNone(out.source_listing_url)
        self.assertIsNone(out.external_case_number)
        self.assertIsNone(out.source_last_checked_at)


if __name__ == "__main__":
    unittest.main()
