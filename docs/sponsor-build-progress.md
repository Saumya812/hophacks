# FindMyPal — Sponsor Build Progress

**Phase completed:** S0 only (audit, accounts, runnable baseline)  
**Date:** 2026-09-19  
**Product name preserved:** FindMyPal  
**Primary database (confirmed):** Supabase PostgreSQL — **single operational source of truth** for current cases/sightings.

This file tracks sponsor-aware phases. Later phases must be requested explicitly. Do not treat the hour budget as a guarantee.

---

## S0 gate status

| Gate requirement | Result |
|------------------|--------|
| Four existing flows documented | **Met** — see below + evidence doc |
| Failures documented | **Met** — Gemini model 404; no realtime; no tests/deploy configs |
| Database ownership explicit | **Met** — Supabase owns cases/sightings; no outbox yet |
| Sponsor service boundaries explicit | **Met** — matrix below; none integrated except partial Gemini |
| Credentials verified safely (no secret printing) | **Met** — presence + live probes only |
| App preserved (no replacement scaffold) | **Met** |

**S0 STOP.** No S1+ implementation in that turn.

### Post-S0 advanced AI batch (2026-09-19, separate request)

Implemented (not sponsor Spacetime/Tiger/etc.):

| Feature | Status |
|---------|--------|
| Face recognition matching | Done — `POST /faces/match` + homepage panel (Rekognition / DeepFace / Gemini Vision) |
| AI case summarizer | Done — `GET/POST /persons/{id}/summary` on profile |
| Duplicate detection | Done — `POST /persons/check-duplicates` on `/report` |
| Sighting credibility scorer | Done — scored on tip create; shown on timeline |
| Gemini model auto-resolve | Done — fixes prior `gemini-1.5-flash` 404 |
| Migration `db/migrations/002_intelligence.sql` | Added — run in Supabase |

Still remaining from the large advanced-feature list: NL alerts, marimo/Spacetime viz, social kit, zip alerts, tip clustering, ElevenLabs calls, Backboard memory, Snowflake patterns, etc.

---

## Runnable baseline (executed 2026-09-19)

| Check | Result |
|-------|--------|
| `GET /health` | Pass — `{"status":"healthy"}` |
| Backend OpenAPI routes present | Pass — persons, sightings, search/natural, lookup/* |
| Frontend `http://localhost:5173/` | Pass — HTTP 200 |
| Supabase `users` / `persons` / `sightings` reachable | Pass |
| `GET /persons?status=active` | Pass — 1 active case |
| `GET /persons/{id}` + sightings | Pass — 1 sighting on sample case |
| `POST /search/natural` | **Fail** — Gemini model `gemini-1.5-flash` returns 404 for this API key/version |
| Automated test suite | **Absent** — no `tests/`, no CI |
| Docker / DigitalOcean App Spec / Procfile | **Absent** |

Local processes observed running during audit: FastAPI (`uvicorn` :8000), Vite (`npm run dev` :5173).

---

## What exists today (implementation vs aspiration)

### Working / real

- **React + Tailwind + Vite** frontend with navy `#1a2b4a` theme
- **FastAPI** backend with CORS
- **Supabase** as operational DB via `supabase-py` + service role key
- **Leaflet** maps on `/person/:id` (last-known + sightings) and `/lookup` report heatmap
- **Client flyer PDF** (`jspdf` + QR) on profile page
- **Server lookup PDF** (`reportlab`) for Smart Person Search reports
- **Mock user** seed (`MOCK_USER_ID` / `mock@findmypal.local`) — not real auth
- Pages: `/`, `/person/:id`, `/report`, `/tip/:id`, **plus** `/lookup` (Smart Person Search — beyond original four-page brief)

### Partial / broken

- **Gemini:** key is configured (`GEMINI_API_KEY=SET`) but live NL search fails with model-not-found for `gemini-1.5-flash`. Keyword search on homepage still works without Gemini.
- **Lookup scrapers:** SerpAPI / NewsAPI / YouTube / RapidAPI keys unset; DuckDuckGo + Reddit public search used as fallbacks. Not a live SerpAPI/NewsAPI/Twitter demonstration.
- **Auth / RLS:** schema comments mention RLS later; app uses service role; no end-user JWT; emails on sightings are returned to public GET.

### Missing (required by later sponsor phases)

- Feedback types / observation-time fields / searched-no-sighting geometry
- Reviewer panel, evidence snapshots, append-only review decisions
- Transactional **outbox** co-committed with mutations
- SpacetimeDB client/server, Live/Reconnecting/Offline UX
- Tiger Data / Timescale projection + `/analytics/case-activity`
- marimo Activity explorer embed
- Backboard memory / per-participant assistant isolation
- Snowflake SQL API reference search + NamUs/synthetic reference dataset
- ElevenLabs TTS + audio cache
- DigitalOcean App Platform configs / worker process
- GoDaddy domain wiring
- Solana — deferred per brief

---

## Four core flows (and known failures)

1. **Homepage search + active cases (`/`)**  
   - Keyword list/filter via `GET /persons` — **works**.  
   - Natural language mode via `POST /search/natural` — **currently fails** (Gemini model 404). Ordinary keyword path remains usable.

2. **Report a case (`/report` → `POST /persons`)**  
   - Creates Supabase `persons` row — **works** (verified earlier in session; list still shows seeded “Test Person”).

3. **Profile + map + flyer (`/person/:id`)**  
   - Loads person + sightings; Leaflet markers; downloadable flyer — **works** (no automated UI test; code path present).  
   - No live updates when another browser adds a tip (manual refresh only).

4. **Public tip (`/tip/:id` → `POST .../sightings`)**  
   - Inserts sighting with lat/lng — **works**.  
   - No SpacetimeDB fan-out; other open profile tabs do not update until refetch.

**Additional page (not in original four):** `/lookup` Smart Person Search — implemented; depends on optional scraper keys + Gemini extraction (heuristic fallback if Gemini fails).

---

## Architecture (current + planned sponsor roles)

```
[Browser React]
   |  REST
[FastAPI]
   |  supabase-py (service role)
[Supabase PostgreSQL]  <--- CURRENT sole source of truth (persons, sightings, users)
```

**Planned (not built):**

| Concern | Owner | Notes |
|---------|-------|-------|
| Cases, tips, feedback, reviews, snapshots, outbox | **Supabase** | Additive migrations only in later phases |
| Minimal change events to browsers | **SpacetimeDB** | Browser refetches canonical FastAPI data; Leaflet renders |
| Time-bucket analytics projection | **Tiger Data** | Rebuildable; not case truth |
| Read-only reference search | **Snowflake** | Parameterized SQL API; separate from demo cases |
| Search preference memory | **Backboard** | Scoped per demo participant; not case facts |
| Filter interpretation / grounded drafts | **Gemini** | Allowlisted filters only; no executable SQL |
| Approved-text audio | **ElevenLabs** | Cache by text hash + case version |
| Activity explorer UI | **marimo** | Server-side; embed on profile, not a new product homepage |
| Hosting | **DigitalOcean App Platform** | FastAPI + static + worker + marimo; do **not** migrate primary DB to DO Managed PG unless explicitly chosen |
| Domain | **GoDaddy** | After team purchase only |

**Outbox rule (planned for S1):** same Supabase transaction as mutation; per-destination delivery tracking; retries with stable event IDs; no sync dependency on every sponsor; no exactly-once claim.

---

## Sponsor status matrix

| Sponsor / system | Role | Code present? | Credentials | Integration status | Demo claim allowed? |
|------------------|------|---------------|-------------|--------------------|---------------------|
| Supabase | Operational SoT | Yes | `SUPABASE_URL`, `SUPABASE_KEY` SET | **Live service** (persons/sightings) | Yes — cases/tips |
| Gemini | NL filters + lookup extraction | Yes (`services/gemini.py`, `gemini_processor.py`) | `GEMINI_API_KEY` SET | **Broken live call** (model 404) | No success claim until model fixed |
| Leaflet / OSM | Maps + Nominatim geocode | Yes | N/A (public tiles/Nominatim) | **Live** | Yes |
| SpacetimeDB | Realtime event distribution | **No** | None | Unavailable | No |
| Tiger Data | Activity time-series | **No** | None | Unavailable | No |
| Snowflake | Reference SQL search | **No** | None | Unavailable | No |
| Backboard | Search memory | **No** | None | Unavailable | No |
| ElevenLabs | TTS | **No** | None | Unavailable | No |
| marimo | Analytics panel | **No** | None | Unavailable | No |
| DigitalOcean | Hosting | **No deploy files** | Account not verified in-repo | Plan only (S0) | No “deployed” claim |
| GoDaddy | Domain | **No** | None | Not purchased / not connected | No |
| SerpAPI / NewsAPI / YouTube / RapidAPI | Lookup scrapers | Optional code paths | Unset | Unavailable / fallback scrapers only | Do not claim paid scrapers |
| Solana | Optional receipt | **No** | None | Deferred | No |
| NamUs / Forge / Bloomberg APIs | Dataset / theme | **No** | None | Not invented; await team export/rubric | No |

---

## Environment variable names (no values)

**Configured / used today**

- `SUPABASE_URL`, `SUPABASE_KEY`
- `GEMINI_API_KEY`
- `CORS_ORIGINS`
- `MOCK_USER_ID`, `MOCK_USER_EMAIL`
- `SERPAPI_KEY`, `NEWSAPI_KEY`, `YOUTUBE_API_KEY`, `RAPIDAPI_KEY`, `TWITTER_RAPIDAPI_HOST`
- Frontend: `VITE_API_BASE_URL`

**Expected in later phases (not in `.env.example` yet)**

- SpacetimeDB: e.g. `SPACETIMEDB_URI`, `SPACETIMEDB_DB`, `SPACETIMEDB_TOKEN` (names TBD after SDK choice)
- Tiger: connection / API vars TBD after capability check
- Snowflake: account/user/role/warehouse/database + key-pair or token vars
- Backboard: API key + workspace/assistant mapping store
- ElevenLabs: `ELEVENLABS_API_KEY`, voice/model IDs
- marimo: serve URL / internal auth between FastAPI and notebook process

---

## Credential / data blockers (early)

1. **Gemini model ID mismatch** — blocks NL search demo until ListModels + code update.  
2. **No SpacetimeDB / Tiger / Snowflake / Backboard / ElevenLabs accounts or keys in repo.**  
3. **No NamUs CSV export** in repo — S4 must use labeled synthetic Snowflake data unless team supplies export.  
4. **No DigitalOcean App Spec**; deployment not authorized in this phase.  
5. **Prize / Bloomberg / Forge rubrics** not present in repo — do not invent requirements.  
6. **Sighting `submitter_email` exposed on public GET** — privacy boundary work needed before public event payloads (S1).

---

## Minimal DigitalOcean deployment plan (prepare only — do not deploy)

**Goal:** host static frontend + FastAPI + future outbox worker (+ marimo later) without moving primary DB off Supabase.

1. **Components**
   - Static site: Vite `frontend/dist` (or DO static site / App Platform static job)
   - Service: `uvicorn main:app` from `backend/`
   - Worker (S1+): small outbox poller process (same image, different run command)
   - marimo (S3+): separate process, internal-only if possible
2. **Secrets via App Platform env** — same names as local; never bake into images.
3. **CORS** — set `CORS_ORIGINS` to the real HTTPS frontend origin.
4. **Health** — use existing `GET /health`.
5. **SPA routing** — catch-all to `index.html` for `/person/*`, `/tip/*`, `/lookup`.
6. **Migrations** — run additive SQL against Supabase (not DO Managed PG) unless team explicitly migrates.
7. **Do not** purchase domains, claim credits, or create billable resources without an explicit action request + established account/budget.

**Current status:** no DO config in repo; no verified existing DO deployment found.

---

## Privacy / demo data rules (carry forward)

- Use **fictional** cases for interactive tips, reviews, health-context demos; label demo status.  
- Keep any future real NamUs reference records **read-only** and visually separate.  
- Exclude emails/private notes from public API responses, events, audio, analytics, AI prompts, exports.  
- Preserve meaning of existing `confidence_level` (1–5 reporter certainty).  
- Three non-sightings must never “clear” a positive sighting (S1 assessment UX).

---

## Next phase (when requested)

**S1 — core feedback, linked map, and SpacetimeDB**

Will require: additive Supabase migrations (feedback, outbox, snapshots/reviews), profile-page panels (not new top-level product pages), SpacetimeDB publish/subscribe with refetch, Live/Reconnecting/Offline states, and evidence updates in `docs/sponsor-evidence.md`.

Do **not** start S1 until explicitly requested.
