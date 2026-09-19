"""
Sightings / mention density heatmap builders.

Used by:
  - FastAPI embed routes (iframe in the React app)
  - marimo notebook `notebooks/sightings_heatmap.py`

Builds a real Folium HeatMap (not decorative Leaflet circles).
Uses Carto basemap tiles — OSM.org volunteer tile servers block many apps (403).
"""

from __future__ import annotations

import html as html_lib
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# Arlington / DC-ish default when no tips (FindMyPal demo geography)
_DEFAULT_CENTER = (38.8691, -77.0540)

# Esri World Street Map — free public tiles (no API key). Avoid Carto CDN
# (watermarks "API KEY REQUIRED") and tile.openstreetmap.org (often 403).
_BASEMAP_TILES = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/"
    "MapServer/tile/{z}/{y}/{x}"
)
_SATELLITE_TILES = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/"
    "MapServer/tile/{z}/{y}/{x}"
)
_SATELLITE_ATTR = (
    'Tiles &copy; <a href="https://www.esri.com/">Esri</a> — Source: Esri, Maxar, Earthstar Geographics'
)


def _normalize_points(points: Sequence[Dict[str, Any]]) -> List[Tuple[float, float, float]]:
    """Return [[lat, lng, weight], ...] for Folium HeatMap."""
    out: List[Tuple[float, float, float]] = []
    for p in points:
        try:
            lat = float(p.get("lat") if "lat" in p else p.get("location_lat"))
            lng = float(p.get("lng") if "lng" in p else p.get("location_lng"))
            if abs(lat) > 90 or abs(lng) > 180:
                continue
            weight = float(p.get("weight") or p.get("count") or 1)
            weight = max(0.25, min(weight, 20.0))
            out.append((lat, lng, weight))
        except (TypeError, ValueError):
            continue
    return out


def _empty_heatmap_html(title: str) -> str:
    safe = html_lib.escape(title)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{safe}</title>
<style>
  body {{ margin:0; font-family: Georgia, 'Times New Roman', serif; background:#f4f6f9; color:#1a2b4a; }}
  .wrap {{ display:flex; align-items:center; justify-content:center; min-height:100vh; padding:2rem; text-align:center; }}
  h1 {{ font-size:1.5rem; font-weight:normal; margin:0 0 .5rem; }}
  p {{ margin:0; font-family: system-ui, sans-serif; font-size:.9rem; color:#4d6786; max-width:28rem; line-height:1.45; }}
</style></head>
<body><div class="wrap"><div>
  <h1>{safe}</h1>
  <p>No geocoded tips yet. Submit community tips with a map location, and the density heatmap will light up here.</p>
</div></div></body></html>"""


def build_folium_heatmap_html(
    points: Sequence[Dict[str, Any]],
    *,
    title: str = "Sightings heatmap",
    zoom_start: int = 11,
) -> str:
    """
    Build a standalone Folium map HTML string with a density HeatMap layer.
    """
    heat_data = _normalize_points(points)
    if not heat_data:
        return _empty_heatmap_html(title)

    try:
        import folium
        from folium.plugins import HeatMap, Fullscreen
    except ImportError as exc:  # pragma: no cover
        logger.error("folium not installed: %s", exc)
        return (
            "<!doctype html><html><body style='font-family:sans-serif;padding:2rem'>"
            "<p>Heatmap unavailable — install <code>folium</code> on the backend.</p>"
            "</body></html>"
        )

    center_lat = sum(p[0] for p in heat_data) / len(heat_data)
    center_lng = sum(p[1] for p in heat_data) / len(heat_data)
    center = (center_lat, center_lng)

    fmap = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles=None,
        control_scale=True,
    )
    folium.TileLayer(
        tiles=_BASEMAP_TILES,
        attr=_BASEMAP_ATTR,
        name="Streets",
        max_zoom=19,
        overlay=False,
        control=True,
    ).add_to(fmap)
    folium.TileLayer(
        tiles=_SATELLITE_TILES,
        attr=_SATELLITE_ATTR,
        name="Satellite",
        max_zoom=19,
        overlay=False,
        control=True,
    ).add_to(fmap)
    Fullscreen().add_to(fmap)

    expanded: List[List[float]] = []
    for lat, lng, w in heat_data:
        copies = max(1, int(round(w)))
        for _ in range(copies):
            expanded.append([lat, lng, min(w, 1.0) + 0.35])

    HeatMap(
        expanded,
        min_opacity=0.35,
        max_zoom=16,
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

    for p in points:
        try:
            lat = float(p.get("lat") if "lat" in p else p.get("location_lat"))
            lng = float(p.get("lng") if "lng" in p else p.get("location_lng"))
        except (TypeError, ValueError):
            continue
        label = p.get("label") or p.get("description") or "Sighting"
        when = p.get("date_time") or p.get("date") or ""
        weight = p.get("weight") or p.get("count") or 1
        popup = folium.Popup(
            f"<strong>{html_lib.escape(str(label))}</strong><br/>weight={html_lib.escape(str(weight))}"
            + (f"<br/>{html_lib.escape(str(when))}" if when else ""),
            max_width=260,
        )
        folium.CircleMarker(
            location=(lat, lng),
            radius=5,
            color="#1a2b4a",
            fill=True,
            fill_color="#1a2b4a",
            fill_opacity=0.7,
            popup=popup,
        ).add_to(fmap)

    safe_title = html_lib.escape(title)
    title_html = f"""
    <div style="position:fixed;top:12px;left:50%;transform:translateX(-50%);
                z-index:9999;background:rgba(26,43,74,0.92);color:#fff;
                padding:8px 16px;font-family:Georgia,serif;font-size:15px;
                border-radius:2px;pointer-events:none;">
      {safe_title} · {len(heat_data)} point{'s' if len(heat_data) != 1 else ''}
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(title_html))
    folium.LayerControl(position="topright", collapsed=False).add_to(fmap)
    return fmap.get_root().render()


def points_from_sighting_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Map DB sighting rows → heatmap points."""
    points: List[Dict[str, Any]] = []
    for r in rows:
        try:
            lat = float(r["location_lat"])
            lng = float(r["location_lng"])
        except (KeyError, TypeError, ValueError):
            continue
        cred = r.get("credibility_score")
        weight = 1.0
        if cred is not None:
            try:
                weight = max(1.0, float(cred) / 3.0)
            except (TypeError, ValueError):
                weight = 1.0
        points.append(
            {
                "lat": lat,
                "lng": lng,
                "weight": weight,
                "label": (r.get("description") or "Community tip")[:120],
                "date_time": r.get("date_time") or r.get("created_at"),
                "id": r.get("id"),
            }
        )
    return points


def points_from_lookup_locations(locations: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Map lookup geocode aggregates → heatmap points."""
    points: List[Dict[str, Any]] = []
    for loc in locations:
        try:
            lat = float(loc["lat"])
            lng = float(loc["lng"])
        except (KeyError, TypeError, ValueError):
            continue
        count = loc.get("count") or 1
        try:
            weight = float(count)
        except (TypeError, ValueError):
            weight = 1.0
        points.append(
            {
                "lat": lat,
                "lng": lng,
                "weight": weight,
                "count": count,
                "label": loc.get("label") or "Mentioned place",
            }
        )
    return points
