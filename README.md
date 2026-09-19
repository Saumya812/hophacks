# FindMyPal

Missing-persons platform: report cases, submit sightings, search with natural language, view tips on a map, and run **Smart Person Search** across public web sources.

**Tech stack:** React + Tailwind · FastAPI · Supabase (PostgreSQL) · Leaflet · Google Gemini · SpacetimeDB (planned) · DigitalOcean

---

## Project structure

```
hophacks/
├── db/
│   └── schema.sql
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── schemas.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── routers/
│   │   ├── persons.py
│   │   ├── sightings.py
│   │   ├── search.py
│   │   └── lookup_router.py      # Smart Person Search API
│   └── services/
│       ├── gemini.py             # NL case search filters
│       ├── scraper_service.py    # Parallel public-source scrapers
│       ├── gemini_processor.py   # Sighting extraction + geocode
│       └── lookup_pdf.py         # Lookup report PDF
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── api.js
    │   ├── components/           # + ReportCard.jsx
    │   └── pages/                # + Lookup.jsx (/lookup)
    └── package.json
```

---

## Status

| Component | Status |
|-----------|--------|
| Database schema (`db/schema.sql`) | Done |
| FastAPI backend (persons / sightings / NL search) | Done |
| React frontend (cases, report, tip, profile) | Done |
| Leaflet map + flyer PDF | Done |
| **Smart Person Search (`/lookup`)** | Done |
| SpacetimeDB realtime | Later |
| DigitalOcean deploy | Later |

**Out of scope (v1):** auth, admin dashboard, payments, face recognition, permanent search history DB.

---

## 1. Database setup (Supabase)

1. Create a Supabase project at [supabase.com](https://supabase.com).
2. Open **SQL Editor** → paste and run [`db/schema.sql`](db/schema.sql).
3. Tables: `users`, `persons`, `sightings`.
4. Seed mock user: `mock@findmypal.local` / `00000000-0000-0000-0000-000000000001`.

Copy from **Project Settings → API**:
- **Project URL** → `SUPABASE_URL` (`https://<ref>.supabase.co`)
- **service_role** key → `SUPABASE_KEY`

---

## 2. Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
```

Fill `backend/.env` (Supabase + Gemini recommended). Optional lookup keys:

```
SERPAPI_KEY=
NEWSAPI_KEY=
YOUTUBE_API_KEY=
RAPIDAPI_KEY=
TWITTER_RAPIDAPI_HOST=twitter-api45.p.rapidapi.com
```

```bash
uvicorn main:app --reload --port 8000
```

### Core API routes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/persons` | Create missing-person profile |
| `GET` | `/persons` | List / filter profiles |
| `GET` | `/persons/{id}` | Single profile |
| `POST` | `/persons/{id}/sightings` | Submit tip |
| `GET` | `/persons/{id}/sightings` | List tips |
| `POST` | `/search/natural` | Gemini NL case search |

### Smart Person Search routes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/lookup/search` | Name + photo → structured report |
| `GET` | `/lookup/report/{id}` | Cached report JSON (1 hour) |
| `GET` | `/lookup/report/{id}/pdf` | Download PDF brief |

**Pipeline:** parallel scrapers (SerpAPI/DuckDuckGo, Reddit, NewsAPI, X, YouTube + `site:` operators for IG/FB/TikTok) → Gemini extraction → Nominatim geocode → report. Rate limit: **5 searches / IP / hour**. Photos stay in memory only (never written to disk).

---

## 3. Frontend setup

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

Open http://localhost:5173

| Path | Purpose |
|------|---------|
| `/` | Homepage — search + active cases |
| `/person/:id` | Profile — timeline, map, flyer PDF |
| `/report` | Create missing-person form |
| `/tip/:id` | Public tip submission |
| `/lookup` | **Smart Person Search** (input → loading → report) |

---

## Design notes

- Color scheme: navy `#1a2b4a` and white
- Fonts: Fraunces (display) + Source Sans 3 (body)
- Mock user only (no auth)
- Lookup report styled as a clean intelligence brief
