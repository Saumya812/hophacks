-- =============================================================================
-- Migration 003 — advanced community / family / alert / safety features
-- Additive & backward compatible. Run in Supabase SQL Editor.
-- =============================================================================

-- Person case management / safety
ALTER TABLE persons
    ADD COLUMN IF NOT EXISTS verified_police_report BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS found_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS found_message TEXT,
    ADD COLUMN IF NOT EXISTS watchers_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS shares_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS tips_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS suspicious_flags INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS under_review BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS demo_tag TEXT;

COMMENT ON COLUMN persons.verified_police_report IS 'True when family-entered police report # is treated as verified badge';
COMMENT ON COLUMN persons.last_verified_at IS 'Family confirmation for 90-day expiry renewal';
COMMENT ON COLUMN persons.watchers_count IS 'People watching / subscribed to this case';
COMMENT ON COLUMN persons.shares_count IS 'Share button / social kit copy count';
COMMENT ON COLUMN persons.tips_count IS 'Cached tip count for engagement score';

-- Case updates (family broadcaster)
CREATE TABLE IF NOT EXISTS case_updates (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id   UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    author_email TEXT,
    body        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_case_updates_person ON case_updates(person_id, created_at DESC);

-- Coordinators (mock roles — not real auth)
CREATE TABLE IF NOT EXISTS case_coordinators (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id   UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    email       TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'coordinator'
                    CHECK (role IN ('coordinator', 'owner')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (person_id, email)
);

-- NL alerts + zip alerts + case watchers
CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind            TEXT NOT NULL CHECK (kind IN ('natural_language', 'zip', 'case_watch')),
    email           TEXT NOT NULL,
    query_text      TEXT,
    zip_code        TEXT,
    person_id       UUID REFERENCES persons(id) ON DELETE CASCADE,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alerts_kind ON alert_subscriptions(kind) WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_alerts_person ON alert_subscriptions(person_id) WHERE active = TRUE;

-- Tip clusters (3+ tips same area within 48h)
CREATE TABLE IF NOT EXISTS tip_clusters (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id       UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    center_lat      DOUBLE PRECISION NOT NULL,
    center_lng      DOUBLE PRECISION NOT NULL,
    radius_km       DOUBLE PRECISION NOT NULL DEFAULT 1.5,
    tip_count       INTEGER NOT NULL,
    window_start    TIMESTAMPTZ NOT NULL,
    window_end      TIMESTAMPTZ NOT NULL,
    label           TEXT,
    notified        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tip_clusters_person ON tip_clusters(person_id, created_at DESC);

-- Suspicious profile flags
CREATE TABLE IF NOT EXISTS profile_flags (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id   UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    reason      TEXT,
    reporter_ip TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Backboard-style search memory (local stand-in when Backboard unavailable)
CREATE TABLE IF NOT EXISTS search_memory (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_key TEXT NOT NULL,
    city            TEXT,
    date_from       DATE,
    date_to         DATE,
    filters_json    JSONB,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (participant_key)
);

-- Outbound email log (no SMTP required for demo)
CREATE TABLE IF NOT EXISTS email_outbox_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    to_email    TEXT NOT NULL,
    subject     TEXT NOT NULL,
    body        TEXT NOT NULL,
    kind        TEXT,
    meta        JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Live tip feed buffer is process-memory; optional persistence of last tips
CREATE TABLE IF NOT EXISTS live_tip_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id   UUID REFERENCES persons(id) ON DELETE SET NULL,
    person_name TEXT,
    snippet     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_live_tips_created ON live_tip_events(created_at DESC);

-- Seed last_verified_at for existing rows
UPDATE persons
SET last_verified_at = COALESCE(last_verified_at, created_at)
WHERE last_verified_at IS NULL;
