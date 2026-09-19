# FindMyPal marimo notebooks

## Baltimore civic story (start here for the viz prize)

```bash
cd backend
.venv\Scripts\activate
pip install marimo pandas folium httpx
marimo run ../notebooks/baltimore_civic_story.py
```

1. Keep FindMyPal API running on `:8000`.
2. Click **Load Layer 1 + Layer 2 map**.
3. **Layer 1** — anonymized tip density across all *active* cases (`/analytics/baltimore/tip-clusters`).
4. **Layer 2** — live CitiWatch camera locations from Baltimore open data.
5. Compare: tip clusters far from cameras → volunteer focus zones (not investigation proof).

Optional: paste one person UUID to add a single-case heatmap layer.  
If no tips fall in the Baltimore box (e.g. demo tips in Arlington), the notebook falls back to all active tips so Layer 1 still shows.

Also see Dashboard in the web app for the same run instructions.

## Other notebooks

| File | Purpose |
|------|---------|
| `baltimore_civic_story.py` | Tip clusters vs CitiWatch cameras |
| `sightings_heatmap.py` | Per-case tip density |
| `case_activity.py` | Case activity charts |
