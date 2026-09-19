/**
 * Shared free basemap tiles — no API key required.
 * Avoid Carto CDN (now watermarks "API KEY REQUIRED") and
 * tile.openstreetmap.org (blocks many clients with 403).
 */
export const BASEMAP_URL =
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}'

export const BASEMAP_ATTR =
  'Tiles &copy; <a href="https://www.esri.com/">Esri</a> — Source: Esri, OpenStreetMap'
