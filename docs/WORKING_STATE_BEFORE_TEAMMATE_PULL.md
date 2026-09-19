# FindMyPal — working state snapshot (before teammate DB pull)

**Captured:** 2026-09-19  
**Purpose:** After you pull teammate DB/schema changes, use this to restore compatibility without rewriting product features.

**Rule:** Supabase remains source of truth. Prefer additive `IF NOT EXISTS` migrations. Do not drop columns our code still reads.

---

## Product features that are working (do not lose)

### Core app
| Feature | How it works | DB dependency |
|---------|--------------|---------------|
| Active cases list / Home gallery | `GET /persons?status=active` | `persons.status`, photo, last_seen_* |
| Report form `/report` | `POST /persons` | `persons` core columns + optional `owner_token`, `contact_email` |
| Profile `/person/:id` | person + sightings + tabs | `persons`, `sightings` |
| Tip form `/tip/:id` | `POST .../sightings` | `sightings` lat/lng, date_time, description, confidence_level 1–5 |
| Lookup `/lookup` | scrapers + Gemini | mostly non-DB; optional face match vs `persons` |
| Flyer PDF | client jspdf | no DB |
| Found `/found` | `status=found` list | `persons.status`, `found_at` / `found_date` |

### Tip → notify → verify pipeline (new)
| Feature | Path | DB / env |
|---------|------|----------|
| Browse `/report-missing` | active cases cards | `persons` |
| TipForm on profile Tips tab | `POST .../sightings` | same as tips; optional `tip_type` |
| EmailJS police/family notify | after tip insert | env only; needs `contact_email` for family |
| `POST /persons/{id}/verify-found` | code `POLICE-*` | sets `status=found`, `found_at`/`found_date`, `found_notes`, `verified_by` |
| Supabase Realtime tips/status | frontend `supabaseClient.js` | Replication on `persons`, `sightings` + anon key |
| Found overlay + toast | profile / found page | status update events |

### Baltimore / marimo (sponsor)
| Feature | Path | Dependency |
|---------|------|------------|
| Layer 1 tip clusters | `GET /analytics/baltimore/tip-clusters` | active `persons` + `sightings` lat/lng only |
| Layer 2 CitiWatch | live ArcGIS (or `/analytics/baltimore/cameras`) | network, not DB |
| Nearest cameras on profile | `GET /analytics/baltimore/nearest/{id}` | tips lat/lng + last_seen geocode |
| Marimo notebook | `notebooks/baltimore_civic_story.py` | API :8000 + GIS |

### Other advanced (graceful if tables missing)
Case updates, alerts, coordinators, clusters, search_memory, live_tip_events, case_source_links, AI summary, credibility scoring — most already try/except or degrade.

---

## SQL files our branch expects (run order)

1. `db/schema.sql` — `users`, `persons`, `sightings` baseline  
2. `db/migrations/002_intelligence.sql` — `ai_summary*`, tip `credibility_*`  
3. `db/migrations/003_advanced_features.sql` — found_*, counters, alert_*, case_*, tip_clusters, search_memory, live_tip_events, email_outbox_log  
4. `db/migrations/004_owner_and_privacy.sql` — `owner_token`, `contact_email`, `last_seen_time`  
5. `db/migrations/005_case_sources.sql` — source_* columns + `case_source_links`  
6. `db/schema_additions.sql` — `found_date`, `found_notes`, `verified_by`, `tip_type` (pipeline)

All use `IF NOT EXISTS` where possible — safe to re-run after teammate changes **if** their changes don’t rename/drop core columns.

---

## Columns / contracts we must keep compatible

### `persons` (critical)
`id`, `name`, `age`, `gender`, `last_seen_location`, `last_seen_date`, `description`, `photo_url`, `status` (`active`|`found`|`closed`), `police_report_number`, `created_at`

### `persons` (important for current UI)
`ai_summary`, `ai_summary_updated_at`, `verified_police_report`, `last_verified_at`, `found_at`, `found_message`, `watchers_count`, `shares_count`, `tips_count`, `contact_email`, `owner_token`, `last_seen_time`, `source_listing_url`, `source_agency_name`, `external_case_number`, `source_last_checked_at`, `found_date`, `found_notes`, `verified_by`

### `sightings` (critical)
`id`, `person_id`, `location_lat`, `location_lng`, `date_time`, `description`, `confidence_level` (**integer 1–5**), `submitter_email`, `created_at`

### `sightings` (important)
`credibility_score`, `family_review_flag`, `credibility_reasons`, `tip_type`

**Do not change `confidence_level` to text (`high`/`medium`/`low`)** without a mapping layer — API and TipForm map UI → 1–5.

---

## Routes to protect (additive only)

| Method | Path | Notes |
|--------|------|-------|
| GET/POST | `/persons`, `/persons/{id}` | core |
| GET/POST | `/persons/{id}/sightings` | tips + notify hook |
| POST | `/persons/{id}/verify-found` | police pipeline (ours) |
| POST | `/persons/{id}/found` | owner mark found (existing) |
| GET | `/analytics/baltimore/tip-clusters` | marimo Layer 1 |
| GET | `/analytics/baltimore/cameras` | camera proxy |
| GET | `/analytics/baltimore/nearest/{id}` | soft camera suggestions |
| GET | `/analytics/baltimore/civic` | dashboard meta |
| GET | `/analytics/heatmap/{id}` | per-case heatmap |

Frontend routes: `/`, `/person/:id`, `/report`, `/report-missing`, `/tip/:id`, `/lookup`, `/found`, `/dashboard`

---

## Env vars (no secrets in this file)

**Backend:** `SUPABASE_URL`, `SUPABASE_KEY`, `GEMINI_API_KEY`, optional EmailJS + police email, optional ElevenLabs/Backboard/Spacetime  

**Frontend:** `VITE_API_BASE_URL`, optional `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` (Realtime)

**Supabase dashboard:** Realtime replication enabled for `persons` + `sightings`

---

## After teammate pull — reconciliation checklist

1. **Diff DB** — list their new tables/columns vs this file; note renames/drops.  
2. **Re-run ours if missing** — migrations `002`→`005` + `schema_additions.sql` (IF NOT EXISTS).  
3. **Smoke API**  
   - `GET /health`  
   - `GET /persons?status=active`  
   - `GET /persons/{id}/sightings`  
   - `GET /analytics/baltimore/tip-clusters?baltimore_only=false`  
   - `POST /persons/{id}/verify-found` with `{"code":"WRONG"}` → expect **403**  
4. **Smoke UI** — `/report-missing` → profile → TipForm; Dashboard marimo instructions; `/found`.  
5. **If they renamed columns** — add adapters in routers (map old→new) rather than rewriting the frontend.  
6. **If they changed `status` enum** — keep `active` / `found` meanings or map aliases.  
7. **Update this doc** with final merged schema.

---

## Explicit non-goals / honest limits (still true)

- No live CCTV / face-on-cameras  
- SpacetimeDB = polling / Supabase Realtime stand-in  
- EmailJS only sends if keys set  
- Marimo Layer 1 needs geocoded tips; Baltimore box may fall back to all tips for demo
