-- =============================================================================
-- Migration 005 — original case source + optional source library links
-- Additive & backward compatible. Run in Supabase SQL Editor.
-- =============================================================================

ALTER TABLE persons
    ADD COLUMN IF NOT EXISTS source_listing_url TEXT,
    ADD COLUMN IF NOT EXISTS source_agency_name TEXT,
    ADD COLUMN IF NOT EXISTS external_case_number TEXT,
    ADD COLUMN IF NOT EXISTS source_last_checked_at DATE;

COMMENT ON COLUMN persons.source_listing_url IS 'Optional HTTP(S) link to the original public listing (community-provided)';
COMMENT ON COLUMN persons.source_agency_name IS 'Optional agency or source name for the original listing';
COMMENT ON COLUMN persons.external_case_number IS 'Optional external case/reference # (separate from police_report_number)';
COMMENT ON COLUMN persons.source_last_checked_at IS 'Date the original listing was last checked by the reporter (date-only)';

-- Lightweight per-case source links (read mostly; write only with existing owner auth)
CREATE TABLE IF NOT EXISTS case_source_links (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id       UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    url             TEXT NOT NULL,
    source_type     TEXT NOT NULL DEFAULT 'other'
                        CHECK (source_type IN ('agency_listing', 'news_article', 'public_appeal', 'other')),
    published_at    DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_case_source_links_person
    ON case_source_links (person_id, created_at DESC);

-- Exact URL dedupe per case (query string preserved)
CREATE UNIQUE INDEX IF NOT EXISTS idx_case_source_links_url_unique
    ON case_source_links (person_id, url);
