# FindMyPal — Sponsor Evidence Log

## SpacetimeDB migration — 2026-09-19

All 12 application tables use native SpacetimeDB storage. The original 1 user, 2 cases and 4 sightings were backed up, copied and verified. The isolated native integration suite passed all 12 tests, covering the API case lifecycle, private-table authorization, rollback, counters, retries and secondary tables. A real anonymous SDK subscription received a committed tip activity event without private fields. Frontend production build and module TypeScript checks passed. The running API returned `{"status":"healthy","database":"spacetimedb"}` and the frontend returned HTTP 200 on port 5173. See [setup and reproducible checks](spacetimedb.md).

The following entries are historical; their Supabase and polling-fallback descriptions have been superseded.

**Purpose:** Record what was actually exercised. Never claim fabricated success, prize eligibility, training improvements, or live sponsor integration without executed proof.

**Legend — integration evidence types**

| Type | Meaning |
|------|---------|
| **Live service** | Real network call to the named provider succeeded in this environment |
| **Cached result** | Served from an intentional short-lived cache after a prior live call |
| **Explicit fixture** | Labeled local/synthetic data; does **not** exercise the sponsor service |
| **Unavailable** | Missing credentials, SDK, or endpoint; UI/API must say so honestly |

---

## S0 — Baseline evidence (2026-09-19)

### Repository inspection

| Item | Finding | Evidence type |
|------|---------|---------------|
| Primary DB | Supabase PostgreSQL (`users`, `persons`, `sightings` in `db/schema.sql`) | Live service (table reads OK) |
| Other DB engines in app | None as operational SoT | N/A |
| Auth | Mock user env + seed row; no JWT login | Explicit fixture / mock |
| Realtime | No SpacetimeDB / WS / SSE client code | Unavailable |
| Outbox | Not present | Unavailable |
| Feedback / reviews / snapshots | Not present | Unavailable |
| Tests | No test directory / CI configs found | Unavailable |
| Deploy configs | No Dockerfile, App Platform spec, compose, Procfile | Unavailable |
| Pages | `/`, `/person/:id`, `/report`, `/tip/:id`, `/lookup` | Code present |

### Environment variable presence (names only; values never logged)

| Variable | Presence at audit |
|----------|-------------------|
| `SUPABASE_URL` | SET |
| `SUPABASE_KEY` | SET |
| `GEMINI_API_KEY` | SET |
| `CORS_ORIGINS` | SET |
| `MOCK_USER_ID` / `MOCK_USER_EMAIL` | SET |
| `SERPAPI_KEY` | UNSET_OR_PLACEHOLDER |
| `NEWSAPI_KEY` | UNSET_OR_PLACEHOLDER |
| `YOUTUBE_API_KEY` | UNSET_OR_PLACEHOLDER |
| `RAPIDAPI_KEY` | UNSET_OR_PLACEHOLDER |
| `TWITTER_RAPIDAPI_HOST` | SET (host string only) |
| SpacetimeDB / Tiger / Snowflake / Backboard / ElevenLabs / marimo vars | **Not defined** |

### Executed runtime proofs

| Action | Result | Evidence type |
|--------|--------|---------------|
| `GET http://127.0.0.1:8000/health` | `healthy` | Live service (local API) |
| Supabase select on `persons` / `users` / `sightings` via backend client | Reachable; ~1 person | Live service |
| `GET /persons?status=active` | `count=1` | Live service |
| `GET /persons/{id}` for `263eaef9-7084-4ab0-8815-619d8179b97e` | Returned “Test Person” | Live service |
| `GET /persons/{id}/sightings` | `count=1` | Live service |
| `GET http://localhost:5173/` | HTTP 200 | Live service (local Vite) |
| OpenAPI lists `/lookup/*` routes | Present | Code + live OpenAPI |
| `POST /search/natural` with query `active cases in Baltimore` | **HTTP error** — `gemini-1.5-flash` not found for API version / method | Live service call **failed** (Gemini configured but broken model ID) |

### Sponsor feature ledger (current)

| Sponsor | Feature in product today | Code path | Live demo action available? | Status |
|---------|--------------------------|-----------|-----------------------------|--------|
| Supabase | Persist cases & tips | `database.py`, `routers/persons.py`, `routers/sightings.py`, `db/schema.sql` | Create/list/get via API/UI | Live service |
| Gemini | NL case filters | `services/gemini.py` → `POST /search/natural` | Attempted; **fails** | Unavailable for demo until model fix |
| Gemini | Lookup mention extraction | `services/gemini_processor.py` | Lookup may fall back to heuristics | Partial / unproven live success in S0 |
| Leaflet | Case map / lookup heatmap | `SightingsMap.jsx`, `ReportCard.jsx` | Open profile / lookup report | Live (tiles) |
| PDF flyer | Profile download | `FlyerButton.jsx` | Button on profile | Local generation (not a cloud sponsor) |
| Lookup PDF | Report download | `services/lookup_pdf.py` | After lookup report | Local generation |
| SpacetimeDB | — | — | No | Unavailable |
| Tiger Data | — | — | No | Unavailable |
| Snowflake | — | — | No | Unavailable |
| Backboard | — | — | No | Unavailable |
| ElevenLabs | — | — | No | Unavailable |
| marimo | — | — | No | Unavailable |
| DigitalOcean | Hosting | — | No deploy performed | Unavailable (plan only in progress doc) |
| GoDaddy | Domain | — | No | Unavailable |

### Incomplete features (must stay hidden or labeled unavailable in later UI)

- Cross-browser live map updates  
- Feedback taxonomy / explainable assessment / reviewer panel  
- Tiger / marimo analytics  
- Snowflake reference inspector  
- ElevenLabs read-aloud / audio appeal  
- Backboard remembered search across sessions  
- Any NamUs “live national registry” framing without an authorized export  

### Privacy note observed in current API

`GET /persons/{id}/sightings` returns `submitter_email` when present. Later phases must exclude private emails from public responses, event payloads, audio, analytics, AI prompts, and exports.

---

## Template for later phases (do not fill with invented proofs)

```
### S# — <phase name> — <date>
| Sponsor | Feature | Code path | Demo action | Evidence type | Result |
|---------|---------|-----------|-------------|---------------|--------|
| ... | ... | ... | ... | Live/Cached/Fixture/Unavailable | ... |
```

---

## Prize / rubric note

No Bloomberg, Forge, or event prize rubric files were found in the repository during S0. Eligibility and sponsor-specific dataset requirements are **not claimed**. Confirm with organizers before pitching.
