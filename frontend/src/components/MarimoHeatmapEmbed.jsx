/**
 * Heatmap embed used on case profile + lookup reports.
 * Prefer React Leaflet density map (reliable). Folium/marimo remains available
 * via notebooks/sightings_heatmap.py and /analytics/heatmap/.../embed for the
 * marimo track.
 */
import { useMemo } from 'react'
import DensityHeatMap from './DensityHeatMap.jsx'
import { API_BASE } from '../api.js'

export default function MarimoHeatmapEmbed({
  personId,
  points,
  lastSeenLocation = '',
  title = 'Location heatmap',
  heightClass = 'h-80 sm:h-[28rem]',
  sightings = null,
}) {
  const normalized = useMemo(() => {
    if (Array.isArray(points) && points.length) {
      return points
        .map((p) => ({
          lat: Number(p.lat ?? p.location_lat),
          lng: Number(p.lng ?? p.location_lng),
          weight: Number(p.weight ?? p.count ?? 1) || 1,
          label: p.label || p.description || 'Mention',
          date: p.date || p.date_time || '',
        }))
        .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng))
    }
    if (Array.isArray(sightings) && sightings.length) {
      return sightings
        .map((s) => ({
          lat: Number(s.location_lat),
          lng: Number(s.location_lng),
          weight: s.credibility_score != null ? Math.max(1, Number(s.credibility_score) / 3) : 1,
          label: s.description || 'Community tip',
          date: s.date_time || '',
        }))
        .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng))
    }
    return []
  }, [points, sightings])

  return (
    <div className="space-y-2">
      <DensityHeatMap
        points={normalized}
        lastSeenLocation={lastSeenLocation}
        title={title}
        heightClass={heightClass}
      />
      {personId ? (
        <p className="text-xs text-navy/45">
          Marimo notebook uses the same data via{' '}
          <a
            className="underline"
            href={`${API_BASE}/analytics/heatmap/${personId}`}
            target="_blank"
            rel="noreferrer"
          >
            /analytics/heatmap/{personId}
          </a>
          . Optional Folium embed:{' '}
          <a
            className="underline"
            href={`${API_BASE}/analytics/heatmap/${personId}/embed`}
            target="_blank"
            rel="noreferrer"
          >
            open
          </a>
          .
        </p>
      ) : null}
    </div>
  )
}
