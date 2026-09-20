# FindMyPal

Missing-persons platform: publish cases, collect tips, search with natural language, map sightings, and run **Smart Person Search** across public web sources.

**Stack:** React + Vite + Tailwind · FastAPI · SpacetimeDB · Leaflet · Google Gemini · Apify (optional) · marimo notebooks

---

## Project structure

```
hophacks/
├── README.md
├── db/
│   ├── schema.sql                 # Core tables
│   └── migrations/                # Intelligence + advanced features
├── notebooks/
│   ├── sightings_heatmap.py       # marimo density heatmap
│   └── case_activity.py           # marimo activity charts
├── docs/                          # Sponsor / build notes
├── backend/
│   ├── main.py
│   ├── config.py · database.py · schemas.py
│   ├── requirements.txt · .env.example
│   ├── routers/                   # persons, sightings, search, lookup, intelligence, features
│   └── services/                  # scrapers, Gemini, maps, alerts, face match, TTS, …
└── frontend/
    ├── src/
    │   ├── App.jsx · api.js · advancedApi.js · mapTiles.js
    │   ├── components/            # maps, lookup report, case tools, live feed, …
    │   └── pages/                 # Home, Lookup, Report, Tip, Profile, Dashboard
    └── package.json
```

---

## Features

| Area | What you get |
|------|----------------|
| Cases | Create / list profiles, tip submission, flyer PDF |
| Maps | Leaflet tip path map + density heatmap (Esri basemap) |
| Search | Gemini natural-language case filters |
| Lookup | Public-web + Apify scrape → Gemini extract → **chronological sighting claims** → geocode → PDF |
| Intelligence | Case summary, credibility scoring, face-match assist |
| Advanced | Live tips, city dashboard, alerts, coordinators, social kit, TTS |

---

## 1. Database (SpacetimeDB)

Follow [SpacetimeDB setup and restart instructions](docs/spacetimedb.md). All application tables now live in SpacetimeDB, and the homepage receives native live updates. Start the persistent local database with `bash scripts/spacetime.sh start`. Historical SQL files are retained for migration reference.

---

## 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
copy .env.example .env          # or: cp .env.example .env
```

Fill `backend/.env` (see `.env.example`). Important keys:

| Key | Purpose |
|-----|---------|
| `SPACETIMEDB_URI` / `SPACETIMEDB_DATABASE` / `SPACETIMEDB_TOKEN` | Database endpoint, name and private publishing identity |
| `GEMINI_API_KEY` | NL search + Lookup extraction (+ optional `GEMINI_MODEL`) |
| `SERPAPI_KEY` | Google + YouTube search (Lookup) |
| `NEWSAPI_KEY` | News mentions |
| `APIFY_TOKEN` | Reddit / Instagram / Facebook crawlers |
| `YOUTUBE_API_KEY` | Optional; SerpAPI YouTube engine is used if unset |
| `RAPIDAPI_KEY` | Optional X/Twitter |

```bash
uvicorn main:app --reload --port 8000
```

Docs: http://127.0.0.1:8000/docs

### Core routes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/persons` | Create case |
| `GET` | `/persons` | List / filter |
| `GET` | `/persons/{id}` | Case detail |
| `POST` | `/persons/{id}/sightings` | Submit tip |
| `GET` | `/persons/{id}/sightings` | List tips |
| `POST` | `/search/natural` | Gemini NL search |

### Smart Person Search

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/lookup/search` | Name + photo → report |
| `GET` | `/lookup/report/{id}` | Cached JSON (1 hour) |
| `GET` | `/lookup/report/{id}/pdf` | PDF brief |

**Pipeline:** SerpAPI / News / X / YouTube / Reddit (+ Apify when configured) → Gemini extraction (with strict heuristic fallback) → geocode → heatmap points. Rate limit: **20 searches / IP / hour**. Photos stay in memory only.

**Apify:** [Console → Integrations](https://console.apify.com/settings/integrations) → set `APIFY_TOKEN`. Defaults: `scrapeforge/reddit-scraper`, `apify/instagram-scraper`, `scraper_one/facebook-posts-search`.

### Maps / analytics

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/geo/search?q=` | Backend geocode proxy |
| `GET` | `/analytics/heatmap/{id}` | Tip points JSON (marimo) |
| `GET` | `/analytics/heatmap/{id}/embed` | Folium HTML embed |

---

## 3. Frontend

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

Open http://localhost:5173

| Path | Purpose |
|------|---------|
| `/` | Home — search, active cases, live tips |
| `/lookup` | Smart Person Search |
| `/person/:id` | Profile — heatmap, tip map, tools, web intel |
| `/report` | Create a case |
| `/tip/:id` | Submit a tip |
| `/dashboard` | City / cross-case dashboard |

Set `VITE_API_BASE=http://127.0.0.1:8000` in `frontend/.env` if needed.

---

## 4. marimo notebooks (optional)

```bash
cd backend
.venv\Scripts\activate
pip install marimo pandas folium httpx
```

**Baltimore civic story (sponsor viz):**
```bash
marimo run ../notebooks/baltimore_civic_story.py
```
Loads public CitiWatch camera locations and optionally overlays FindMyPal tip heatmaps.
Also linked from the in-app **Dashboard**.

**Per-case tip heatmap:**
```bash
marimo run ../notebooks/sightings_heatmap.py
```

API helpers:
- `GET /analytics/baltimore/civic` — notebook metadata
- `GET /analytics/baltimore/cameras` — camera points proxy
- `GET /analytics/heatmap/{id}` — tip points for overlay

---

## Design

- Navy `#1a2b4a` + white
- Fraunces (display) + Source Sans 3 (body)
- Mock user only (no production auth)
- Lookup report styled as an intelligence brief

---

## Notes

- Do **not** commit `backend/.venv`, `__pycache__`, or `.env` files (see `.gitignore`).
- Gemini free-tier quotas can force Lookup onto a strict heuristic fallback; set a working `GEMINI_API_KEY` / model for best extract quality.
- Map tiles use Esri World Street Map (no Carto/OSM.org tile key required).
