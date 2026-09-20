# FindMyPal — Devpost copy-paste

Use these fields on Devpost. Adjust links if your tunnel/repo URL changed.

---

## Project name
FindMyPal

## Tagline (≤60 chars ideal)
Community tips, live maps, and AI search for missing persons.

## Built with (tags)
React, Vite, Tailwind CSS, FastAPI, SpacetimeDB, Google Gemini, Leaflet, Esri, ElevenLabs, Cloudflare, GoDaddy, Apify, marimo, Python, JavaScript

## Demo / try it
- Live demo (Cloudflare quick tunnel — keep laptop running):  
  https://mortgages-ship-myrtle-transparent.trycloudflare.com  
- Local: frontend `:5174` · API `:8000` · SpacetimeDB `:3000`  
- Domain path: findmypal.us (GoDaddy + Cloudflare; named tunnel when zone is Active)

## GitHub repo
https://github.com/Saumya812/hophacks

---

## Inspiration

There are tens of thousands of active missing-person cases in the U.S. Families still rely on flyers and fragmented Facebook posts. Tips get lost; maps don’t update; searching the open web is overwhelming.

We built **FindMyPal** so communities can publish cases, share tips with locations, see them live on a map, and use AI to search both in-app cases and public web mentions — carefully labeled as community information, not official law-enforcement data.

---

## What it does

FindMyPal is a missing-persons platform with two lanes:

### 1) Cases (inside the app)
- **Home gallery** — browse active cases; click a face to open the profile  
- **Missing / Found** — lists of active and reunited cases  
- **Report** — file a case (photo, last seen, description) with **duplicate detection**  
- **Tips** — submit sightings with location + confidence; **credibility scoring** on the timeline  
- **Maps** — Leaflet tip path + **density heatmap**  
- **Flyer PDF + QR** — printable outreach in one click  
- **AI case summary** (Gemini) — plain-English brief of the case + tips  
- **Natural-language search** — e.g. “active cases near Baltimore”  
- **Live updates** — SpacetimeDB subscriptions for tip / found activity  
- **Family tools** — share kit, mark found, renew, flag, optional **ElevenLabs** audio brief  
- **Dashboard** — city-level stats and patterns (awareness, not certainty)

### 2) Lookup (Smart Person Search)
- Enter a name (+ optional photo)  
- Scrape / search public sources → **Gemini extraction** of sighting-like claims  
- Geocode → map / PDF brief  
- Photos stay session-only; reports are not proof of a sighting

Demo reunited cases are labeled: *Not a real missing person — FindMyPal hackathon demo only.*

---

## How we built it

```
Browser (React + Vite + Tailwind)
    → FastAPI (:8000)
        → SpacetimeDB (cases, tips, activity — live WS)
        → Gemini (NL search, Lookup extract, summaries)
        → Geocoders + Esri/Leaflet maps
        → Optional: SerpAPI / News / Apify / ElevenLabs TTS
```

- **Frontend:** React Router pages (Home, Missing, Found, Report, Tip, Lookup, Profile, Dashboard)  
- **Backend:** FastAPI routers for persons, sightings, search, lookup, intelligence, features  
- **Database:** SpacetimeDB as source of truth (migrated from earlier Supabase prototype)  
- **Realtime:** native Spacetime subscriptions + light poll backup  
- **Demo deploy:** Cloudflare Tunnel in front of Vite (API proxied same-origin); GoDaddy holds **findmypal.us**

---

## Challenges we ran into

1. **Realtime + privacy** — SpacetimeDB public activity vs private tip fields; refetch sensitive data through FastAPI.  
2. **Lookup quality** — Gemini quota / model issues forced a **strict heuristic fallback** so we don’t invent sightings.  
3. **Found-case UX** — profiles were bouncing to `/found` on open; fixed so only a live “just found” transition celebrates.  
4. **Deploying findmypal.us** — GoDaddy domain + Cloudflare nameserver cutover vs fast **trycloudflare** demos for judging.  
5. **Gallery / landing polish** — balancing a distinctive photo wall with usable spacing and clickable cases (Rules of Hooks crash on profile was a hard bug).

---

## Accomplishments that we're proud of

- End-to-end product: report → tip → map → summary → flyer → found  
- SpacetimeDB as live SoT with real tip activity on the client  
- Lookup pipeline that structures messy public-web noise into a readable brief  
- Honest product language (unverified tips, demo disclaimers)  
- Sponsor-aware stack: Gemini, SpacetimeDB, ElevenLabs, Cloudflare, GoDaddy, maps/notebooks

---

## What we learned

- Missing-person UX must be calm, clear, and never overclaim certainty  
- AI is most valuable as **structuring and ranking**, not as a verdict  
- Realtime is worthless if private fields leak — keep private rows on the API  
- For hackathons, a **quick tunnel** beats fighting nameservers the night before

---

## What's next for FindMyPal

- Stable production on DigitalOcean + **findmypal.us** named tunnel / DNS  
- Real auth + family ownership tokens (not mock user)  
- Stronger Lookup source coverage and caching without lowering accuracy  
- Shareable Gemini → ElevenLabs audio bulletin link  
- Partner with local orgs; keep the “not affiliated with LE” boundary clear

---

## Inspiration / “Built for” (sponsor tracks — claim only what you demoed)

| Sponsor | How we used it |
|---------|----------------|
| **SpacetimeDB** | Primary DB + live case_activity subscriptions |
| **Google Gemini** | NL search, Lookup extraction, case summaries |
| **ElevenLabs** | Case brief TTS audio |
| **Cloudflare** | Public HTTPS demo tunnel |
| **GoDaddy** | findmypal.us domain registration |
| **DigitalOcean** | Planned droplet hosting path |
| **Leaflet / Esri** | Tip maps + heatmaps |
| **marimo** | Analytics / Baltimore civic notebooks |
| **Apify / SerpAPI** (when keyed) | Deeper public-web crawl for Lookup |

---

## Short “About the project” blurb (if Devpost has a short box)

FindMyPal helps families and communities publish missing-person cases, collect location tips on live maps, and search both in-app cases and the public web with Gemini — powered by FastAPI, SpacetimeDB, and Leaflet — with clear disclaimers that tips are unverified community information.

---

## Screenshots checklist (upload on Devpost)

1. Home photo gallery  
2. Case profile (overview + tip timeline)  
3. Tips & Map / heatmap  
4. Lookup report  
5. Dashboard stats  
6. Found page (demo reunited cases)

---

## Cover image / thumbnail tip

Use the cream Home hero + gallery, or a profile hero with ACTIVE + LIVE badge — high contrast, readable title **FindMyPal**.
