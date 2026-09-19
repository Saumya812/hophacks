-- =============================================================================
-- FindMyPal — Supabase (PostgreSQL) Schema
-- =============================================================================
-- Run this file in the Supabase SQL Editor (or via psql) to provision the DB.
-- Tables: users, persons, sightings
-- =============================================================================

-- Enable UUID generation (Supabase usually has this already; safe to re-run)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- users
-- Stores account identity. Auth is mocked in the app for now; this table still
-- exists so sightings / roles can reference a real user row later.
-- role: 'family' (case submitter) | 'public' (tip submitter)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL UNIQUE,
    role        TEXT NOT NULL DEFAULT 'public'
                    CHECK (role IN ('family', 'public')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  users IS 'FindMyPal user accounts (mock auth; family or public role)';
COMMENT ON COLUMN users.role IS 'family = case reporter; public = tip submitter';

-- -----------------------------------------------------------------------------
-- persons
-- One row per missing-person case / profile.
-- status: 'active' | 'found' | 'closed'
-- last_seen_location is free-text (city / address); lat/lng live on sightings.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS persons (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                 TEXT NOT NULL,
    age                  INTEGER NOT NULL CHECK (age >= 0 AND age <= 150),
    gender               TEXT,
    last_seen_location   TEXT NOT NULL,
    last_seen_date       DATE NOT NULL,
    description          TEXT NOT NULL,
    photo_url            TEXT,
    status               TEXT NOT NULL DEFAULT 'active'
                             CHECK (status IN ('active', 'found', 'closed')),
    police_report_number TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  persons IS 'Missing person case profiles';
COMMENT ON COLUMN persons.status IS 'active = still missing; found / closed = resolved';
COMMENT ON COLUMN persons.last_seen_location IS 'Human-readable last known place (not lat/lng)';

-- Helpful indexes for list + filter endpoints
CREATE INDEX IF NOT EXISTS idx_persons_name
    ON persons (LOWER(name));

CREATE INDEX IF NOT EXISTS idx_persons_status
    ON persons (status);

CREATE INDEX IF NOT EXISTS idx_persons_last_seen_location
    ON persons (LOWER(last_seen_location));

CREATE INDEX IF NOT EXISTS idx_persons_age
    ON persons (age);

CREATE INDEX IF NOT EXISTS idx_persons_created_at
    ON persons (created_at DESC);

-- -----------------------------------------------------------------------------
-- sightings
-- Public tips / reported sightings linked to a person.
-- confidence_level: 1 (low) .. 5 (high)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sightings (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id         UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    location_lat      DOUBLE PRECISION NOT NULL
                          CHECK (location_lat >= -90 AND location_lat <= 90),
    location_lng      DOUBLE PRECISION NOT NULL
                          CHECK (location_lng >= -180 AND location_lng <= 180),
    date_time         TIMESTAMPTZ NOT NULL,
    description       TEXT NOT NULL,
    confidence_level  INTEGER NOT NULL DEFAULT 3
                          CHECK (confidence_level >= 1 AND confidence_level <= 5),
    submitter_email   TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  sightings IS 'Reported sightings / tips for a missing person';
COMMENT ON COLUMN sightings.confidence_level IS 'Submitter confidence 1 (low) to 5 (high)';
COMMENT ON COLUMN sightings.location_lat IS 'WGS84 latitude of the sighting';
COMMENT ON COLUMN sightings.location_lng IS 'WGS84 longitude of the sighting';

CREATE INDEX IF NOT EXISTS idx_sightings_person_id
    ON sightings (person_id);

CREATE INDEX IF NOT EXISTS idx_sightings_date_time
    ON sightings (date_time DESC);

CREATE INDEX IF NOT EXISTS idx_sightings_created_at
    ON sightings (created_at DESC);

-- -----------------------------------------------------------------------------
-- Seed: mock user used by the backend when auth is not implemented
-- -----------------------------------------------------------------------------
INSERT INTO users (id, email, role)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'mock@findmypal.local',
    'family'
)
ON CONFLICT (email) DO NOTHING;
