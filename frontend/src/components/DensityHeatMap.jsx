/**
 * DensityHeatMap — Leaflet density map (Esri basemap + leaflet.heat).
 * Used for:
 *  - Live sightings heatmap (case tips)
 *  - Lookup location heatmap (geocoded mentions)
 *  - Falls back gracefully when empty
 */
import { useEffect, useMemo, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, Marker, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet.heat'
import { API_BASE } from '../api.js'
import { BASEMAP_ATTR, BASEMAP_URL } from '../mapTiles.js'

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

const redIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

function FitPoints({ points, fallback }) {
  const map = useMap()
  useEffect(() => {
    const pts = (points || [])
      .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng))
      .map((p) => [p.lat, p.lng])
    const apply = () => {
      if (pts.length === 0) {
        if (fallback) map.setView(fallback, 12)
        return
      }
      if (pts.length === 1) {
        map.setView(pts[0], 13)
      } else {
        map.fitBounds(pts, { padding: [40, 40] })
      }
      // Leaflet often paints blank until size is recalculated after mount
      setTimeout(() => map.invalidateSize(), 50)
      setTimeout(() => map.invalidateSize(), 250)
    }
    apply()
  }, [map, points, fallback])
  return null
}

function HeatLayer({ points }) {
  const map = useMap()
  useEffect(() => {
    if (!points?.length) return undefined
    const latlngs = points.map((p) => {
      const intensity = Math.min(1.0, 0.35 + (Number(p.weight) || 1) * 0.15)
      return [p.lat, p.lng, intensity]
    })
    const layer = L.heatLayer(latlngs, {
      radius: 28,
      blur: 22,
      maxZoom: 17,
      minOpacity: 0.35,
      gradient: {
        0.2: '#1a2b4a',
        0.45: '#3d6b9a',
        0.7: '#e8a838',
        0.9: '#d94f30',
        1.0: '#9b1d1d',
      },
    })
    layer.addTo(map)
    return () => {
      map.removeLayer(layer)
    }
  }, [map, points])
  return null
}

async function geocode(query) {
  if (!query?.trim()) return null
  try {
    const res = await fetch(
      `${API_BASE}/geo/search?q=${encodeURIComponent(query.trim().replace(/,+$/, ''))}`,
    )
    if (!res.ok) return null
    const data = await res.json()
    if (!data?.found) return null
    return { lat: Number(data.lat), lng: Number(data.lng) }
  } catch {
    return null
  }
}

/**
 * @param {{ lat:number, lng:number, weight?:number, label?:string, date?:string }[]} points
 * @param {string} [lastSeenLocation] — geocoded and shown as red marker + heat seed
 * @param {string} [title]
 * @param {string} [heightClass]
 * @param {boolean} [showMarkers]
 */
export default function DensityHeatMap({
  points = [],
  lastSeenLocation = '',
  title = 'Density heatmap',
  heightClass = 'h-80 sm:h-[28rem]',
  showMarkers = true,
}) {
  const [lastKnown, setLastKnown] = useState(null)
  const [geoNote, setGeoNote] = useState('')

  useEffect(() => {
    let cancelled = false
    if (!lastSeenLocation) {
      setLastKnown(null)
      return undefined
    }
    geocode(lastSeenLocation)
      .then((coords) => {
        if (cancelled) return
        setLastKnown(coords)
        setGeoNote(coords ? '' : 'Could not geocode last-known location.')
      })
      .catch(() => {
        if (!cancelled) setGeoNote('Could not geocode last-known location.')
      })
    return () => {
      cancelled = true
    }
  }, [lastSeenLocation])

  const heatPoints = useMemo(() => {
    const out = []
    for (const p of points || []) {
      const lat = Number(p.lat ?? p.location_lat)
      const lng = Number(p.lng ?? p.location_lng)
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue
      out.push({
        lat,
        lng,
        weight: Number(p.weight ?? p.count ?? 1) || 1,
        label: p.label || p.description || 'Point',
        date: p.date || p.date_time || '',
      })
    }
    if (lastKnown) {
      out.push({
        lat: lastKnown.lat,
        lng: lastKnown.lng,
        weight: 1.5,
        label: `Last known: ${lastSeenLocation}`,
        date: '',
      })
    }
    return out
  }, [points, lastKnown, lastSeenLocation])

  const center = heatPoints[0]
    ? [heatPoints[0].lat, heatPoints[0].lng]
    : [38.8691, -77.054]

  return (
    <div className="space-y-2">
      <div className={`${heightClass} w-full overflow-hidden border border-navy/15 bg-navy-50`}>
        {heatPoints.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
            <p className="font-display text-xl text-navy/70">{title}</p>
            <p className="max-w-md text-sm text-navy/55">
              No map points yet. Submit tips with a location, or run a public-web scan that geocodes
              mentions.
            </p>
            {geoNote ? <p className="text-xs text-amber-800">{geoNote}</p> : null}
          </div>
        ) : (
          <MapContainer
            center={center}
            zoom={12}
            scrollWheelZoom
            className="h-full w-full"
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer attribution={BASEMAP_ATTR} url={BASEMAP_URL} />
            <FitPoints
              points={heatPoints}
              fallback={lastKnown ? [lastKnown.lat, lastKnown.lng] : center}
            />
            <HeatLayer points={heatPoints} />

            {lastKnown && (
              <Marker position={[lastKnown.lat, lastKnown.lng]} icon={redIcon}>
                <Popup>
                  <strong>Last known</strong>
                  <br />
                  {lastSeenLocation}
                </Popup>
              </Marker>
            )}

            {showMarkers &&
              heatPoints
                .filter((p) => !lastKnown || p.lat !== lastKnown.lat || p.lng !== lastKnown.lng)
                .map((p, i) => (
                  <CircleMarker
                    key={`${p.lat}-${p.lng}-${i}`}
                    center={[p.lat, p.lng]}
                    radius={6}
                    pathOptions={{
                      color: '#1a2b4a',
                      fillColor: '#1a2b4a',
                      fillOpacity: 0.75,
                      weight: 1,
                    }}
                  >
                    <Popup>
                      <strong>{p.label}</strong>
                      {p.date ? (
                        <>
                          <br />
                          {new Date(p.date).toLocaleString()}
                        </>
                      ) : null}
                      <br />
                      weight {p.weight}
                    </Popup>
                  </CircleMarker>
                ))}
          </MapContainer>
        )}
      </div>
      <p className="text-xs text-navy/55">
        {title} · {heatPoints.length} point{heatPoints.length === 1 ? '' : 's'} · Esri basemap +
        density heat
        {geoNote ? ` · ${geoNote}` : ''}
      </p>
    </div>
  )
}

export { geocode }
