# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "httpx", "pandas", "folium"]
# ///
"""
FindMyPal — Live Sightings Heatmap (marimo)

Real density heatmap from community tip coordinates (Folium HeatMap).

Run:
  pip install marimo httpx pandas folium
  marimo run notebooks/sightings_heatmap.py

Or embed in the app via FastAPI:
  GET /analytics/heatmap/{person_id}/embed
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
    from folium.plugins import HeatMap, Fullscreen
    return Fullscreen, HeatMap, folium, httpx, mo, pd


@app.cell
def _(mo):
    mo.md(
        r"""
        # Live sightings heatmap
        Density map of tip clusters for a FindMyPal case. Hotter areas =
        more tips nearby (weighted by credibility when available).
        """
    )
    return


@app.cell
def _(mo):
    api = mo.ui.text(value="http://127.0.0.1:8000", label="API base")
    person_id = mo.ui.text(value="", label="Person UUID")
    run = mo.ui.run_button(label="Load heatmap")
    mo.vstack([api, person_id, run])
    return api, person_id, run


@app.cell
def _(Fullscreen, HeatMap, api, folium, httpx, mo, pd, person_id, run):
    if not run.value:
        mo.md("Enter a person UUID and click **Load heatmap**.")
        result = None
    elif not person_id.value.strip():
        mo.md("Person UUID is required.")
        result = None
    else:
        base = api.value.rstrip("/")
        pid = person_id.value.strip()
        r = httpx.get(f"{base}/analytics/heatmap/{pid}", timeout=30)
        r.raise_for_status()
        data = r.json()
        points = data.get("points") or []
        df = pd.DataFrame(points)

        if df.empty:
            result = mo.vstack(
                [
                    mo.md("**No geocoded tips yet** for this case."),
                    mo.md(f"Embed URL: `{base}/analytics/heatmap/{pid}/embed`"),
                ]
            )
        else:
            center = [float(df["lat"].mean()), float(df["lng"].mean())]
            fmap = folium.Map(location=center, zoom_start=12, tiles=None)
            folium.TileLayer(
                tiles=(
                    "https://server.arcgisonline.com/ArcGIS/rest/services/"
                    "World_Street_Map/MapServer/tile/{z}/{y}/{x}"
                ),
                attr="Tiles © Esri — Source: Esri, OpenStreetMap",
                name="Esri streets",
            ).add_to(fmap)
            Fullscreen().add_to(fmap)

            heat_rows = []
            for _, row in df.iterrows():
                w = float(row.get("weight") or 1)
                for _ in range(max(1, int(round(w)))):
                    heat_rows.append([float(row["lat"]), float(row["lng"]), min(w, 1.0) + 0.35])

            HeatMap(
                heat_rows,
                min_opacity=0.35,
                radius=22,
                blur=18,
                gradient={
                    0.2: "#1a2b4a",
                    0.45: "#3d6b9a",
                    0.7: "#e8a838",
                    0.9: "#d94f30",
                    1.0: "#9b1d1d",
                },
            ).add_to(fmap)

            for _, row in df.iterrows():
                folium.CircleMarker(
                    location=[float(row["lat"]), float(row["lng"])],
                    radius=5,
                    color="#1a2b4a",
                    fill=True,
                    fill_opacity=0.75,
                    popup=folium.Popup(
                        f"{row.get('label', 'Tip')}<br/>weight={row.get('weight', 1)}",
                        max_width=240,
                    ),
                ).add_to(fmap)

            result = mo.vstack(
                [
                    mo.md(
                        f"**{data.get('count', 0)} tips** · provenance `{data.get('provenance')}` · "
                        f"[open embed]({base}/analytics/heatmap/{pid}/embed)"
                    ),
                    mo.Html(fmap._repr_html_()),
                    mo.ui.table(df) if len(df) else None,
                ]
            )
    result
    return


if __name__ == "__main__":
    app.run()
