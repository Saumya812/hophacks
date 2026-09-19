-- =============================================================================
-- Additive migration: AI intelligence fields (backward compatible)
-- Run in Supabase SQL Editor after schema.sql
-- =============================================================================

ALTER TABLE persons
    ADD COLUMN IF NOT EXISTS ai_summary TEXT,
    ADD COLUMN IF NOT EXISTS ai_summary_updated_at TIMESTAMPTZ;

COMMENT ON COLUMN persons.ai_summary IS 'Gemini/heuristic plain-English case summary';
COMMENT ON COLUMN persons.ai_summary_updated_at IS 'When ai_summary was last regenerated';

ALTER TABLE sightings
    ADD COLUMN IF NOT EXISTS credibility_score INTEGER
        CHECK (credibility_score IS NULL OR (credibility_score >= 1 AND credibility_score <= 10)),
    ADD COLUMN IF NOT EXISTS family_review_flag BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS credibility_reasons TEXT;

COMMENT ON COLUMN sightings.credibility_score IS 'AI/heuristic tip credibility 1-10 (separate from reporter confidence_level)';
COMMENT ON COLUMN sightings.family_review_flag IS 'True when credibility_score >= 7';
COMMENT ON COLUMN sightings.credibility_reasons IS 'Human-readable scoring notes';

CREATE INDEX IF NOT EXISTS idx_sightings_family_review
    ON sightings (person_id)
    WHERE family_review_flag = TRUE;
