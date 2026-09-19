-- =============================================================================
-- FindMyPal — additive columns for tip → notify → verify-found pipeline
-- Safe to re-run. Does not alter existing application logic.
-- =============================================================================

-- Persons: found / verification metadata (found_at / found_message already exist in 003)
ALTER TABLE persons
  ADD COLUMN IF NOT EXISTS found_date timestamptz,
  ADD COLUMN IF NOT EXISTS found_notes text,
  ADD COLUMN IF NOT EXISTS verified_by text;

-- contact_email may already exist from migration 004
ALTER TABLE persons
  ADD COLUMN IF NOT EXISTS contact_email text;

COMMENT ON COLUMN persons.found_date IS 'When authorities marked the person found (verify-found)';
COMMENT ON COLUMN persons.found_notes IS 'Police notes on resolution';
COMMENT ON COLUMN persons.verified_by IS 'e.g. law_enforcement';

-- Sightings: tip category from TipForm
ALTER TABLE sightings
  ADD COLUMN IF NOT EXISTS tip_type text DEFAULT 'general';

COMMENT ON COLUMN sightings.tip_type IS 'saw_person | know_location | have_info | unsure | general';

-- Enable Realtime (Supabase): Dashboard → Database → Replication
-- Also run if publication exists:
-- ALTER PUBLICATION supabase_realtime ADD TABLE persons;
-- ALTER PUBLICATION supabase_realtime ADD TABLE sightings;
