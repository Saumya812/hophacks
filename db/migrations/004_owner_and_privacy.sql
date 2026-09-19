-- =============================================================================
-- Migration 004 — owner token, contact, last-seen time, unique case watch
-- =============================================================================

ALTER TABLE persons
    ADD COLUMN IF NOT EXISTS owner_token TEXT,
    ADD COLUMN IF NOT EXISTS contact_email TEXT,
    ADD COLUMN IF NOT EXISTS last_seen_time TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_alerts_watch_unique
    ON alert_subscriptions (person_id, lower(email))
    WHERE kind = 'case_watch' AND active = TRUE;
