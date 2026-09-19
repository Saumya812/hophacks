# FindMyPal

Missing-persons platform: report cases, submit sightings, search with natural language, and view tips on a map.

**Tech stack:** React + Tailwind · FastAPI · Supabase (PostgreSQL) · Leaflet · Google Gemini · SpacetimeDB (planned) · DigitalOcean

---

## Project structure

```
hophacks/
├── db/
│   └── schema.sql              # Supabase schema (persons, sightings, users)
├── backend/                    # FastAPI API
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── schemas.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── routers/
│   │   ├── persons.py
│   │   ├── sightings.py
│   │   └── search.py
│   └── services/
│       └── gemini.py
└── frontend/                   # React + Tailwind + Leaflet
    ├── src/
    │   ├── App.jsx
    │   ├── api.js
    │   ├── components/         # Layout, PersonCard, SightingsMap, FlyerButton
    │   └── pages/              # Home, PersonProfile, Report, Tip
    ├── .env.example
    └── package.json
```

---

## Status

| Component | Status |
|-----------|--------|
| Database schema (`db/schema.sql`) | Done |
| FastAPI backend | Done |
| React frontend (4 pages) | Done |
| Leaflet map on `/person/:id` | Done |
| Flyer PDF generator | Done |
| SpacetimeDB realtime | Later |
| DigitalOcean deploy | Later |

**Out of scope (v1):** auth, admin dashboard, social sharing, payments.

---

## 1. Database setup (Supabase)

1. Create a Supabase project at [supabase.com](https://supabase.com).
2. Open **SQL Editor** → paste and run [`db/schema.sql`](db/schema.sql).
3. Tables created: `users`, `persons`, `sightings`.
4. Seed mock user: `mock@findmypal.local` / `00000000-0000-0000-0000-000000000001`.

Copy from **Project Settings → API**:
- **Project URL** → `SUPABASE_URL` (must look like `https://<ref>.supabase.co` — not the dashboard URL)
- **service_role** key → `SUPABASE_KEY`

---

## 2. Backend setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows; use `cp` on macOS/Linux
```

Edit `backend/.env` with your Supabase URL/key and optional Gemini key.

```bash
uvicorn main:app --reload --port 8000
```

- Health: http://localhost:8000/health
- Swagger: http://localhost:8000/docs

### API routes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/persons` | Create missing-person profile |
| `GET` | `/persons` | List with filters: `name`, `location`, `age_min`, `age_max`, `status` |
| `GET` | `/persons/{id}` | Single profile |
| `POST` | `/persons/{id}/sightings` | Submit a sighting/tip |
| `GET` | `/persons/{id}/sightings` | All sightings for a person |
| `POST` | `/search/natural` | Gemini NL search → filtered persons |

---

## 3. Frontend setup

Keep the backend running on port 8000, then:

```bash
cd frontend
copy .env.example .env   # Windows; use `cp` on macOS/Linux
npm install
npm run dev
```

Open http://localhost:5173

| Path | Purpose |
|------|---------|
| `/` | Homepage — keyword or Gemini search + active cases |
| `/person/:id` | Profile — timeline, Leaflet map (red last-known / blue sightings), flyer PDF |
| `/report` | Create missing-person form |
| `/tip/:id` | Public tip submission (lat/lng + optional device geolocation) |

`VITE_API_BASE_URL` in `frontend/.env` defaults to `http://127.0.0.1:8000`.

---

## Design notes

- Color scheme: navy `#1a2b4a` and white
- Fonts: Fraunces (display) + Source Sans 3 (body)
- Mock user only (no auth)
- Comments included throughout for hackathon readability
