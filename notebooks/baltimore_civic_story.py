# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "httpx", "pandas", "folium"]
# ///
"""
FindMyPal — Baltimore civic story (marimo)

Layer 1 — FindMyPal tip clusters (anonymized, all active cases)
Layer 2 — Baltimore CitiWatch camera locations (open data)

Comparison: where tips cluster vs where cameras already exist —
volunteer search coordination (not investigation proof).

Run:
  cd backend && .venv\\Scripts\\activate
  pip install marimo pandas folium httpx
  marimo run ../notebooks/baltimore_civic_story.py

Requires FindMyPal API on :8000 for Layer 1.
Layer 2 hits Baltimore GIS directly.
"""

import marimo

__generated_with = "0.13.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import httpx
    import pandas as pd
    import folium
    from folium.plugins import Fullscreen, MarkerCluster, HeatMap

    return Fullscreen, HeatMap, MarkerCluster, folium, httpx, mo, pd


@app.cell
def _(mo):
    mo.md(
        r"""
        # Baltimore: tips vs public cameras

        **Layer 1 — FindMyPal tip clusters**  
        All tips on *active* cases, plotted as a heatmap.  
        **No names, no descriptions** — geographic density only.

        **Layer 2 — CitiWatch camera locations**  
        Baltimore City open data (public infrastructure points, not live video).

        **Why compare them**  
        If tips cluster where cameras are sparse, that is a signal for
        **volunteer search focus** (flyers, awareness walks) — not proof of a sighting.
        """
    )
    return


@app.cell
def _(mo):
    api = mo.ui.text(value="http://127.0.0.1:8000", label="FindMyPal API base")
    cam_limit = mo.ui.slider(100, 1500, value=800, step=100, label="Max cameras to load")
    baltimore_only = mo.ui.checkbox(
        value=True,
        label="Layer 1: keep tips inside Baltimore metro box",
    )
    person_id = mo.ui.text(
        value="",
        label="Optional: highlight one case UUID (extra heatmap layer)",
    )
    run = mo.ui.run_button(label="Load Layer 1 + Layer 2 map")
    mo.vstack([api, cam_limit, baltimore_only, person_id, run])
    return api, baltimore_only, cam_limit, person_id, run


@app.cell
def _(httpx, mo, pd):
    import math as _math

    CAMERAS_URL = (
        "https://geodata.baltimorecity.gov/egis/rest/services/"
        "CityView/CitiWatchCamera/FeatureServer/0/query"
    )

    def load_cameras(limit: int) -> pd.DataFrame:
        r = httpx.get(
            CAMERAS_URL,
            params={
                "where": "1=1",
                "outFields": "CAM_NUMBER,CAM_LOCATION",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "json",
                "resultRecordCount": str(int(limit)),
            },
            timeout=45,
            follow_redirects=True,
            headers={"User-Agent": "FindMyPal-Marimo/1.0"},
        )
        r.raise_for_status()
        data = r.json()
        rows = []
        for feat in data.get("features") or []:
            geom = feat.get("geometry") or {}
            attrs = feat.get("attributes") or {}
            lon, lat = geom.get("x"), geom.get("y")
            if lat is None or lon is None:
                continue
            rows.append(
                {
                    "cam_number": attrs.get("CAM_NUMBER"),
                    "location": attrs.get("CAM_LOCATION") or "CitiWatch camera",
                    "lat": float(lat),
                    "lng": float(lon),
                    "layer": "citiwatch",
                }
            )
        return pd.DataFrame(rows)

    def load_citywide_tips(api_base: str, baltimore_only: bool) -> dict:
        """Layer 1 — anonymized tip density across all active cases."""
        base = api_base.rstrip("/")
        r = httpx.get(
            f"{base}/analytics/baltimore/tip-clusters",
            params={"baltimore_only": str(baltimore_only).lower()},
            timeout=45,
        )
        r.raise_for_status()
        return r.json() or {}

    def load_case_tips(api_base: str, pid: str) -> pd.DataFrame:
        """Optional single-case overlay (still no names on the map)."""
        if not pid.strip():
            return pd.DataFrame()
        base = api_base.rstrip("/")
        r = httpx.get(f"{base}/analytics/heatmap/{pid.strip()}", timeout=30)
        r.raise_for_status()
        points = (r.json() or {}).get("points") or []
        if not points:
            return pd.DataFrame()
        # Drop labels if present — keep density only on the civic map
        rows = [
            {
                "lat": float(p["lat"]),
                "lng": float(p["lng"]),
                "weight": float(p.get("weight") or 1),
                "layer": "single_case",
            }
            for p in points
            if p.get("lat") is not None and p.get("lng") is not None
        ]
        return pd.DataFrame(rows)

    def haversine_m(lat1, lon1, lat2, lon2):
        r = 6371000.0
        p1, p2 = _math.radians(lat1), _math.radians(lat2)
        dphi = _math.radians(lat2 - lat1)
        dl = _math.radians(lon2 - lon1)
        a = (
            _math.sin(dphi / 2) ** 2
            + _math.cos(p1) * _math.cos(p2) * _math.sin(dl / 2) ** 2
        )
        return 2 * r * _math.asin(_math.sqrt(a))

    def tip_camera_gap_stats(tips_df: pd.DataFrame, cams_df: pd.DataFrame, threshold_m=400):
        """Share of tip points farther than threshold_m from any listed camera."""
        if tips_df is None or tips_df.empty or cams_df is None or cams_df.empty:
            return None
        far = 0
        dists = []
        for _, tip in tips_df.iterrows():
            best = None
            for _, cam in cams_df.iterrows():
                d = haversine_m(
                    float(tip["lat"]),
                    float(tip["lng"]),
                    float(cam["lat"]),
                    float(cam["lng"]),
                )
                if best is None or d < best:
                    best = d
            if best is not None:
                dists.append(best)
                if best > threshold_m:
                    far += 1
        if not dists:
            return None
        return {
            "n": len(dists),
            "avg_m": sum(dists) / len(dists),
            "far_n": far,
            "far_pct": 100.0 * far / len(dists),
            "threshold_m": threshold_m,
        }

    return (
        CAMERAS_URL,
        haversine_m,
        load_cameras,
        load_case_tips,
        load_citywide_tips,
        tip_camera_gap_stats,
    )


@app.cell
def _(
    Fullscreen,
    HeatMap,
    MarkerCluster,
    api,
    baltimore_only,
    cam_limit,
    folium,
    load_cameras,
    load_case_tips,
    load_citywide_tips,
    mo,
    pd,
    person_id,
    run,
    tip_camera_gap_stats,
):
    if not run.value:
        result = mo.md(
            "Set options above, then click **Load Layer 1 + Layer 2 map**.\n\n"
            "Keep the FindMyPal API running (`uvicorn` on port 8000) for tip clusters."
        )
    else:
        try:
            cams = load_cameras(int(cam_limit.value))
            tip_payload = load_citywide_tips(api.value, bool(baltimore_only.value))
            # If Baltimore box is empty but tips exist elsewhere (e.g. demo Arlington),
            # fall back so Layer 1 still demos.
            if (
                bool(baltimore_only.value)
                and not (tip_payload.get("points") or [])
                and int(tip_payload.get("count_all_active_tips") or 0) > 0
            ):
                tip_payload = load_citywide_tips(api.value, False)
                tip_payload["_fallback_note"] = (
                    "No tips inside the Baltimore metro box — showing all active-case "
                    "tip points so Layer 1 still demos. Uncheck the Baltimore filter "
                    "to make this explicit."
                )
            tips = pd.DataFrame(tip_payload.get("points") or [])
            if not tips.empty:
                tips["layer"] = "citywide_tips"
            case_tips = load_case_tips(api.value, person_id.value)
            err = None
        except Exception as exc:
            cams = None
            tips = None
            tip_payload = {}
            case_tips = None
            err = str(exc)

        if err:
            result = mo.md(
                f"""
                **Could not load live data:** `{err}`

                - Layer 2 needs network access to `geodata.baltimorecity.gov`
                - Layer 1 needs FindMyPal API: `{api.value}/analytics/baltimore/tip-clusters`
                """
            )
        elif cams is None or cams.empty:
            result = mo.md("No camera rows returned from Baltimore GIS.")
        else:
            if tips is not None and not tips.empty:
                center = [float(tips["lat"].mean()), float(tips["lng"].mean())]
            else:
                center = [float(cams["lat"].mean()), float(cams["lng"].mean())]

            fmap = folium.Map(location=center, zoom_start=12, tiles=None)
            folium.TileLayer(
                tiles=(
                    "https://server.arcgisonline.com/ArcGIS/rest/services/"
                    "World_Street_Map/MapServer/tile/{z}/{y}/{x}"
                ),
                attr="Tiles © Esri — Source: Esri, OpenStreetMap",
                name="Streets",
            ).add_to(fmap)
            Fullscreen().add_to(fmap)

            # --- Layer 1: citywide tip density ---
            if tips is not None and not tips.empty:
                heat = [
                    [
                        float(row["lat"]),
                        float(row["lng"]),
                        min(float(row.get("weight") or 1), 1.0) + 0.35,
                    ]
                    for _, row in tips.iterrows()
                ]
                HeatMap(
                    heat,
                    name="Layer 1 · FindMyPal tip clusters (anonymized)",
                    min_opacity=0.4,
                    radius=24,
                    blur=20,
                ).add_to(fmap)

            # Optional single-case emphasis
            if case_tips is not None and not case_tips.empty:
                case_heat = [
                    [
                        float(row["lat"]),
                        float(row["lng"]),
                        min(float(row.get("weight") or 1), 1.0) + 0.5,
                    ]
                    for _, row in case_tips.iterrows()
                ]
                HeatMap(
                    case_heat,
                    name="Optional · one case tip density",
                    min_opacity=0.35,
                    radius=18,
                    blur=14,
                ).add_to(fmap)

            # --- Layer 2: CitiWatch cameras ---
            cam_group = MarkerCluster(name="Layer 2 · CitiWatch cameras").add_to(fmap)
            for _, row in cams.iterrows():
                folium.CircleMarker(
                    location=[row["lat"], row["lng"]],
                    radius=3,
                    color="#3d4a5c",
                    fill=True,
                    fill_opacity=0.65,
                    popup=folium.Popup(
                        f"Camera {row.get('cam_number')}<br/>{row.get('location')}",
                        max_width=260,
                    ),
                ).add_to(cam_group)

            folium.LayerControl(collapsed=False).add_to(fmap)

            n_cases = tip_payload.get("active_cases", 0)
            n_all = tip_payload.get("count_all_active_tips", tip_payload.get("count", 0))
            n_map = tip_payload.get("count", 0)
            insight = (
                f"**Layer 2:** {len(cams)} CitiWatch listings (cap {int(cam_limit.value)}).  \n"
                f"**Layer 1:** {n_map} anonymized tip points"
                f" from **{n_cases}** active cases"
            )
            if tip_payload.get("baltimore_only"):
                insight += f" (Baltimore box; {n_all} tips citywide before filter)."
            else:
                insight += "."
            if tip_payload.get("_fallback_note"):
                insight += f"  \n_{tip_payload['_fallback_note']}_"

            gap = tip_camera_gap_stats(tips, cams, threshold_m=400)
            if gap:
                insight += (
                    f"  \n**Comparison:** avg tip→nearest camera ≈ **{gap['avg_m']:.0f} m**; "
                    f"**{gap['far_n']}** / {gap['n']} tips "
                    f"(**{gap['far_pct']:.0f}%**) are farther than "
                    f"{gap['threshold_m']} m from a listed camera — "
                    "candidate volunteer focus zones."
                )
            elif tips is None or tips.empty:
                insight += (
                    "  \nNo tip points yet — submit geocoded tips on active cases, "
                    "then reload."
                )

            result = mo.vstack(
                [
                    mo.md(insight),
                    mo.md(
                        """
                        ### Read carefully
                        - Tip layer = **density only** (no personal info).
                        - Cameras = **locations**, not live feeds / face match.
                        - Gaps ≠ “AI said check this camera” — they mean
                          **human volunteers may be more useful there**.
                        - Tips remain unverified community reports.
                        """
                    ),
                    mo.Html(fmap._repr_html_()),
                    mo.ui.table(cams.head(40)),
                ]
            )
    result
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## How this plugs into FindMyPal
        1. Cases & tips live in **Supabase** via FastAPI.
        2. `GET /analytics/baltimore/tip-clusters` → Layer 1 (anonymized).
        3. Baltimore GIS → Layer 2.
        4. Web app: **Dashboard** + case **Tips & Map** (nearest cameras per tip).
        """
    )
    return


if __name__ == "__main__":
    app.run()
